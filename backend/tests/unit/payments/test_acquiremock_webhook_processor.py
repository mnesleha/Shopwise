"""Unit tests for the AcquireMock webhook processor (Slice PR2/3).

Covers:
- PAID event → Payment.SUCCESS + Order.PAID
- FAILED event → Payment.FAILED + Order.PAYMENT_FAILED
- EXPIRED event treated as a failure (same path as FAILED)
- Idempotence: repeated identical event does not re-apply side-effects
- Missing payment (unknown provider_payment_id) raises AcquireMockPaymentNotFound
- Unsupported status string raises ValueError
- Processing is delegated to apply_provider_result (not ad-hoc logic)
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from orders.models import Order
from payments.models import Payment
from payments.providers.acquiremock_webhook import AcquireMockWebhookEvent
from payments.services.acquiremock_webhook_processor import (
    AcquireMockPaymentNotFound,
    process_acquiremock_webhook_event,
)
from shipping.models import Shipment
from tests.conftest import create_valid_order

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_PAYLOAD = {
    "payment_id": "pay_webhook_001",
    "reference": "ref_001",
    "amount": "99.00",
    "status": "PAID",
    "timestamp": "2026-04-01T12:00:00Z",
}


def _make_event(status: str, payment_id: str = "pay_webhook_001") -> AcquireMockWebhookEvent:
    return AcquireMockWebhookEvent(
        payment_id=payment_id,
        reference="ref_001",
        amount="99.00",
        status=status,
        timestamp="2026-04-01T12:00:00Z",
        raw={**_SAMPLE_PAYLOAD, "status": status, "payment_id": payment_id},
    )


def _create_pending_acquiremock_payment(
    provider_payment_id: str = "pay_webhook_001",
) -> tuple[Payment, Order]:
    user = User.objects.create_user(
        email=f"wh_{provider_payment_id}@example.com", password="pass"
    )
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        provider=Payment.Provider.ACQUIREMOCK,
        provider_payment_id=provider_payment_id,
    )
    return payment, order


# ---------------------------------------------------------------------------
# Happy-path status transitions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_paid_webhook_marks_payment_success():
    """PAID event → payment.status == SUCCESS and paid_at is populated."""
    payment, _ = _create_pending_acquiremock_payment()
    process_acquiremock_webhook_event(_make_event("PAID"))

    payment.refresh_from_db()
    assert payment.status == Payment.Status.SUCCESS
    assert payment.paid_at is not None
    assert payment.failed_at is None
    assert payment.failure_reason is None


@pytest.mark.django_db
def test_paid_webhook_marks_order_paid():
    """PAID event → order.status == PAID."""
    payment, order = _create_pending_acquiremock_payment()
    process_acquiremock_webhook_event(_make_event("PAID"))

    order.refresh_from_db()
    assert order.status == Order.Status.PAID


@pytest.mark.django_db
def test_paid_webhook_creates_shipment():
    _, order = _create_pending_acquiremock_payment(provider_payment_id="pay_wh_ship")
    process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_wh_ship"))

    shipment = Shipment.objects.get(order=order)
    assert shipment.provider_code == "MOCK"
    assert shipment.service_code == order.shipping_service_code


@pytest.mark.django_db
def test_failed_webhook_marks_payment_failed():
    """FAILED event → payment.status == FAILED and failed_at is populated."""
    payment, _ = _create_pending_acquiremock_payment(provider_payment_id="pay_wh_fail")
    process_acquiremock_webhook_event(_make_event("FAILED", payment_id="pay_wh_fail"))

    payment.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert payment.failed_at is not None
    assert payment.failure_reason is not None
    assert payment.paid_at is None


@pytest.mark.django_db
def test_failed_webhook_marks_order_payment_failed():
    """FAILED event → order.status == PAYMENT_FAILED."""
    payment, order = _create_pending_acquiremock_payment(provider_payment_id="pay_wh_fail2")
    process_acquiremock_webhook_event(_make_event("FAILED", payment_id="pay_wh_fail2"))

    order.refresh_from_db()
    assert order.status == Order.Status.PAYMENT_FAILED
    assert order.cancel_reason == Order.CancelReason.PAYMENT_FAILED


@pytest.mark.django_db
def test_expired_webhook_treated_as_failure():
    """EXPIRED event is treated as a failure — payment goes to FAILED, order to PAYMENT_FAILED."""
    payment, order = _create_pending_acquiremock_payment(provider_payment_id="pay_wh_exp")
    process_acquiremock_webhook_event(_make_event("EXPIRED", payment_id="pay_wh_exp"))

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert order.status == Order.Status.PAYMENT_FAILED


@pytest.mark.django_db
def test_expired_failure_reason_reflects_expiry():
    """EXPIRED event stores an expiry-specific failure reason, not a generic one."""
    payment, _ = _create_pending_acquiremock_payment(provider_payment_id="pay_wh_exp2")
    process_acquiremock_webhook_event(_make_event("EXPIRED", payment_id="pay_wh_exp2"))

    payment.refresh_from_db()
    assert payment.failure_reason is not None
    assert "expir" in payment.failure_reason.lower()


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_duplicate_success_webhook_is_idempotent():
    """Sending PAID twice does not blow up and leaves payment in SUCCESS."""
    payment, _ = _create_pending_acquiremock_payment(provider_payment_id="pay_idem_ok")
    process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_idem_ok"))
    # Second delivery — must be a safe no-op.
    process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_idem_ok"))

    payment.refresh_from_db()
    assert payment.status == Payment.Status.SUCCESS


@pytest.mark.django_db
def test_duplicate_success_webhook_does_not_create_duplicate_shipment():
    _, order = _create_pending_acquiremock_payment(provider_payment_id="pay_idem_ship")
    process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_idem_ship"))
    process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_idem_ship"))

    assert Shipment.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_duplicate_success_does_not_update_paid_at():
    """Second PAID event must not overwrite paid_at timestamp."""
    payment, _ = _create_pending_acquiremock_payment(provider_payment_id="pay_idem_ts")
    process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_idem_ts"))
    payment.refresh_from_db()
    first_paid_at = payment.paid_at

    process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_idem_ts"))
    payment.refresh_from_db()
    assert payment.paid_at == first_paid_at


@pytest.mark.django_db
def test_duplicate_failure_webhook_is_idempotent():
    """Sending FAILED twice does not blow up and leaves payment in FAILED."""
    payment, _ = _create_pending_acquiremock_payment(provider_payment_id="pay_idem_fail")
    process_acquiremock_webhook_event(_make_event("FAILED", payment_id="pay_idem_fail"))
    process_acquiremock_webhook_event(_make_event("FAILED", payment_id="pay_idem_fail"))

    payment.refresh_from_db()
    assert payment.status == Payment.Status.FAILED


@pytest.mark.django_db
def test_success_after_failure_is_idempotent():
    """An out-of-order PAID after FAILED is treated as already-terminal (no-op)."""
    payment, order = _create_pending_acquiremock_payment(provider_payment_id="pay_idem_oof")
    process_acquiremock_webhook_event(_make_event("FAILED", payment_id="pay_idem_oof"))
    # Simulate a late PAID arriving after FAILED — must be ignored.
    process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_idem_oof"))

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert order.status == Order.Status.PAYMENT_FAILED


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unknown_payment_id_raises_not_found():
    """No matching Payment record → AcquireMockPaymentNotFound is raised."""
    with pytest.raises(AcquireMockPaymentNotFound):
        process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_does_not_exist"))


@pytest.mark.django_db
def test_non_acquiremock_payment_is_not_matched():
    """A DEV_FAKE payment sharing the same provider_payment_id must not be matched."""
    user = User.objects.create_user(email="wh_devfake@example.com", password="pass")
    order = create_valid_order(user=user)
    Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        provider=Payment.Provider.DEV_FAKE,
        provider_payment_id="pay_shared_id",
    )

    with pytest.raises(AcquireMockPaymentNotFound):
        process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_shared_id"))


@pytest.mark.django_db
def test_unsupported_status_raises_value_error():
    """An unknown status string raises ValueError before touching the DB."""
    _create_pending_acquiremock_payment(provider_payment_id="pay_unknown_status")
    with pytest.raises(ValueError, match="Unsupported AcquireMock status"):
        process_acquiremock_webhook_event(
            _make_event("REFUNDED", payment_id="pay_unknown_status")
        )


@pytest.mark.django_db
def test_unsupported_status_does_not_mutate_payment():
    """After ValueError for unknown status, payment stays PENDING."""
    payment, _ = _create_pending_acquiremock_payment(provider_payment_id="pay_no_mutation")
    with pytest.raises(ValueError):
        process_acquiremock_webhook_event(
            _make_event("REFUNDED", payment_id="pay_no_mutation")
        )

    payment.refresh_from_db()
    assert payment.status == Payment.Status.PENDING


# ---------------------------------------------------------------------------
# Delegation verification
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_processor_delegates_to_apply_provider_result():
    """Processor must call the central apply_provider_result, not ad-hoc logic."""
    _create_pending_acquiremock_payment(provider_payment_id="pay_delegate")

    apply_path = "payments.services.acquiremock_webhook_processor.apply_provider_result"
    with patch(apply_path) as mock_apply:
        process_acquiremock_webhook_event(_make_event("PAID", payment_id="pay_delegate"))

    mock_apply.assert_called_once()
    _, kwargs = mock_apply.call_args
    assert kwargs["provider_result"].success is True
