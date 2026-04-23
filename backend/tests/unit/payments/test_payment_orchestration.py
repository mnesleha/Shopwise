"""Tests for payment orchestration / application service (Slice 3).

Covers:
- PaymentOrchestrationService.start_payment() — full happy and sad paths
- apply_provider_result() — isolated payment/order state transitions
- Provider resolution driven by payment_method, not hardcoded
- Guard conditions (already paid, order not payable, unsupported method)
- OrderService backward-compat delegation
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from api.exceptions.payment import OrderNotPayableException, PaymentAlreadyExistsException
from orders.models import Order
from orders.services.order_service import OrderService
from payments.models import Payment
from payments.providers.base import ProviderStartResult
from payments.providers.resolver import ProviderNotConfiguredException
from payments.services.payment_orchestration import PaymentOrchestrationService
from payments.services.payment_result_applier import apply_provider_result
from shipping.models import Shipment
from shipping.statuses import ShipmentStatus
from tests.conftest import create_valid_order

User = get_user_model()


# ---------------------------------------------------------------------------
# apply_provider_result — isolated unit tests (no full orchestration)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_apply_result_success_marks_payment_paid():
    """apply_provider_result(success) sets payment.status=SUCCESS and paid_at."""
    user = User.objects.create_user(email="appl1@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=True)
    apply_provider_result(payment=payment, order=order, provider_result=result)
    payment.refresh_from_db()

    assert payment.status == Payment.Status.SUCCESS
    assert payment.paid_at is not None
    assert payment.failed_at is None
    assert payment.failure_reason is None


@pytest.mark.django_db
def test_apply_result_success_sets_order_paid():
    """apply_provider_result(success) transitions order to PAID."""
    user = User.objects.create_user(email="appl2@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=True)
    apply_provider_result(payment=payment, order=order, provider_result=result)
    order.refresh_from_db()

    assert order.status == Order.Status.PAID


@pytest.mark.django_db
def test_apply_result_success_creates_shipment_for_paid_order(tmp_path):
    user = User.objects.create_user(email="appl_ship_1@example.com", password="pass")
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        order = create_valid_order(
            user=user,
            shipping_provider_code="MOCK",
            shipping_service_code="express",
        )
        payment = Payment.objects.create(
            order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
        )

        result = ProviderStartResult(success=True)
        apply_provider_result(payment=payment, order=order, provider_result=result)

        shipment = Shipment.objects.get(order=order)
        assert shipment.service_code == "express"
        assert shipment.service_name_snapshot == "Express"
        assert shipment.provider_code == "MOCK"
        assert shipment.label_file.name.endswith(".svg")
        assert shipment.label_url.startswith("/media/shipping/labels/")


@pytest.mark.django_db
def test_apply_result_success_is_idempotent_for_shipment_creation():
    user = User.objects.create_user(email="appl_ship_2@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=True)
    apply_provider_result(payment=payment, order=order, provider_result=result)
    apply_provider_result(payment=payment, order=order, provider_result=result)

    assert Shipment.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_apply_result_failure_marks_payment_failed():
    """apply_provider_result(failure) sets payment.status=FAILED, failed_at, failure_reason."""
    user = User.objects.create_user(email="appl3@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=False, failure_reason="Card declined")
    apply_provider_result(payment=payment, order=order, provider_result=result)
    payment.refresh_from_db()

    assert payment.status == Payment.Status.FAILED
    assert payment.failed_at is not None
    assert payment.failure_reason == "Card declined"
    assert payment.paid_at is None


@pytest.mark.django_db
def test_apply_result_failure_sets_order_payment_failed():
    """apply_provider_result(failure) transitions order to PAYMENT_FAILED."""
    user = User.objects.create_user(email="appl4@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=False, failure_reason="Declined")
    apply_provider_result(payment=payment, order=order, provider_result=result)
    order.refresh_from_db()

    assert order.status == Order.Status.PAYMENT_FAILED


@pytest.mark.django_db
def test_apply_result_failure_does_not_create_shipment():
    user = User.objects.create_user(email="appl_ship_3@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=False, failure_reason="Declined")
    apply_provider_result(payment=payment, order=order, provider_result=result)

    assert Shipment.objects.filter(order=order).count() == 0


# ---------------------------------------------------------------------------
# PaymentOrchestrationService.start_payment — happy paths
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_orchestration_success_returns_paid_payment():
    """start_payment with COD/success returns a SUCCESS payment."""
    user = User.objects.create_user(email="orch1@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = PaymentOrchestrationService.start_payment(
        order=order,
        payment_method=Payment.PaymentMethod.COD,
        extra={"simulated_result": "success"},
    )

    assert payment.status == Payment.Status.SUCCESS
    assert payment.provider == Payment.Provider.DEV_FAKE
    assert payment.paid_at is not None


@pytest.mark.django_db
def test_orchestration_failure_returns_failed_payment():
    """start_payment with COD/fail returns a FAILED payment."""
    user = User.objects.create_user(email="orch2@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = PaymentOrchestrationService.start_payment(
        order=order,
        payment_method=Payment.PaymentMethod.COD,
        extra={"simulated_result": "fail"},
    )

    assert payment.status == Payment.Status.FAILED
    assert payment.failed_at is not None
    assert payment.failure_reason is not None


@pytest.mark.django_db
def test_orchestration_none_method_falls_back_to_dev_fake():
    """start_payment with method=None (legacy) still uses DEV_FAKE."""
    user = User.objects.create_user(email="orch3@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = PaymentOrchestrationService.start_payment(
        order=order,
        payment_method=None,
        extra={"simulated_result": "success"},
    )

    assert payment.status == Payment.Status.SUCCESS
    assert payment.provider == Payment.Provider.DEV_FAKE


# ---------------------------------------------------------------------------
# PaymentOrchestrationService — guard conditions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_orchestration_card_resolves_to_acquiremock(monkeypatch):
    """start_payment with CARD uses AcquireMockProvider (resolver wired correctly)."""
    from payments.providers.acquiremock import AcquireMockProvider
    from payments.providers.base import ProviderStartResult

    user = User.objects.create_user(email="orch4@example.com", password="pass")
    order = create_valid_order(user=user)

    # Stub out the HTTP call — we only want to verify the provider is used
    def fake_start(self, context):
        return ProviderStartResult(
            success=True,
            provider_payment_id="mock-id-99",
            redirect_url="https://acquiremock.test/pay/mock-id-99",
        )

    monkeypatch.setattr(AcquireMockProvider, "start", fake_start)

    payment = PaymentOrchestrationService.start_payment(
        order=order,
        payment_method=Payment.PaymentMethod.CARD,
        extra={"return_url": "https://shop.test/return"},
    )

    assert payment.provider == Payment.Provider.ACQUIREMOCK
    assert payment.provider_payment_id == "mock-id-99"


@pytest.mark.django_db
def test_orchestration_raises_if_success_payment_already_exists():
    """start_payment raises PaymentAlreadyExistsException when order already paid."""
    user = User.objects.create_user(email="orch5@example.com", password="pass")
    order = create_valid_order(user=user)

    # First payment succeeds
    PaymentOrchestrationService.start_payment(
        order=order,
        payment_method=Payment.PaymentMethod.COD,
        extra={"simulated_result": "success"},
    )

    order.refresh_from_db()
    with pytest.raises(PaymentAlreadyExistsException):
        PaymentOrchestrationService.start_payment(
            order=order,
            payment_method=Payment.PaymentMethod.COD,
            extra={"simulated_result": "success"},
        )


@pytest.mark.django_db
def test_orchestration_raises_if_order_not_payable():
    """start_payment raises OrderNotPayableException for non-payable order status."""
    user = User.objects.create_user(email="orch6@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.CANCELLED)

    with pytest.raises(OrderNotPayableException):
        PaymentOrchestrationService.start_payment(
            order=order,
            payment_method=Payment.PaymentMethod.COD,
            extra={"simulated_result": "success"},
        )


@pytest.mark.django_db
def test_orchestration_allows_retry_after_failed_payment():
    """start_payment on an order in PAYMENT_FAILED state succeeds (retry is allowed)."""
    user = User.objects.create_user(email="orch7@example.com", password="pass")
    order = create_valid_order(user=user)

    # First attempt fails
    PaymentOrchestrationService.start_payment(
        order=order,
        payment_method=Payment.PaymentMethod.COD,
        extra={"simulated_result": "fail"},
    )
    order.refresh_from_db()
    assert order.status == Order.Status.PAYMENT_FAILED

    # Retry succeeds
    payment = PaymentOrchestrationService.start_payment(
        order=order,
        payment_method=Payment.PaymentMethod.COD,
        extra={"simulated_result": "success"},
    )
    assert payment.status == Payment.Status.SUCCESS


# ---------------------------------------------------------------------------
# Provider is resolved via resolver, not hardcoded
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_orchestration_uses_resolve_provider_not_hardcoded():
    """start_payment calls resolve_provider() — not a hardcoded DevFakeProvider."""
    user = User.objects.create_user(email="orch8@example.com", password="pass")
    order = create_valid_order(user=user)

    mock_provider = MagicMock()
    mock_provider.start.return_value = ProviderStartResult(success=True)
    mock_provider.provider_enum = Payment.Provider.DEV_FAKE  # required by orchestration

    with patch(
        "payments.services.payment_orchestration.resolve_provider",
        return_value=mock_provider,
    ) as mock_resolve:
        PaymentOrchestrationService.start_payment(
            order=order,
            payment_method=Payment.PaymentMethod.COD,
            extra={"simulated_result": "success"},
        )

    mock_resolve.assert_called_once_with(Payment.PaymentMethod.COD)
    mock_provider.start.assert_called_once()


# ---------------------------------------------------------------------------
# OrderService backward-compat delegation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_service_create_payment_still_works_after_delegation():
    """OrderService.create_payment_and_apply_result delegates correctly — success path."""
    user = User.objects.create_user(email="compat1@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = OrderService.create_payment_and_apply_result(
        order=order, result="success", actor_user=user
    )

    assert payment.status == Payment.Status.SUCCESS
    assert payment.provider == Payment.Provider.DEV_FAKE
    assert payment.paid_at is not None
    order.refresh_from_db()
    assert order.status == Order.Status.PAID


@pytest.mark.django_db
def test_order_service_failure_still_works_after_delegation():
    """OrderService.create_payment_and_apply_result delegates correctly — failure path."""
    user = User.objects.create_user(email="compat2@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = OrderService.create_payment_and_apply_result(
        order=order, result="fail", actor_user=user
    )

    assert payment.status == Payment.Status.FAILED
    assert payment.failed_at is not None
    order.refresh_from_db()
    assert order.status == Order.Status.PAYMENT_FAILED


# ---------------------------------------------------------------------------
# Corrective fixes (PR1 review follow-up)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_apply_result_persists_provider_payment_id_when_present():
    """provider_payment_id from ProviderStartResult is saved onto the Payment."""
    user = User.objects.create_user(email="corr1@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=True, provider_payment_id="ext-txn-999")
    apply_provider_result(payment=payment, order=order, provider_result=result)
    payment.refresh_from_db()

    assert payment.provider_payment_id == "ext-txn-999"


@pytest.mark.django_db
def test_apply_result_provider_payment_id_stays_null_when_absent():
    """provider_payment_id remains null when ProviderStartResult does not supply one."""
    user = User.objects.create_user(email="corr2@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=True)  # no provider_payment_id
    apply_provider_result(payment=payment, order=order, provider_result=result)
    payment.refresh_from_db()

    assert payment.provider_payment_id is None


@pytest.mark.django_db
def test_apply_result_success_order_paid_is_owned_by_commit_reservations():
    """commit_reservations_for_paid is always called exactly once on the success path.

    When it is a no-op (e.g. no reservations), the applier's own fallback
    conditional save ensures the order reaches PAID status.  This test patches
    commit_reservations as a no-op and verifies: (a) it is called, (b) payment
    reaches SUCCESS.
    """
    user = User.objects.create_user(email="corr3@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    with patch(
        "payments.services.payment_result_applier.commit_reservations_for_paid",
        wraps=lambda **kwargs: None,  # no-op but track that it was called
    ) as mock_commit:
        result = ProviderStartResult(success=True)
        apply_provider_result(payment=payment, order=order, provider_result=result)

    # commit_reservations_for_paid must be called exactly once
    mock_commit.assert_called_once_with(order=order)

    # After applying the result, payment is SUCCESS
    payment.refresh_from_db()
    assert payment.status == Payment.Status.SUCCESS


# ---------------------------------------------------------------------------
# Deferred flow — COD checkout without explicit simulated_result
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_apply_result_deferred_leaves_payment_pending():
    """apply_provider_result(deferred=True) must leave payment in PENDING state.

    A deferred result means the provider has acknowledged the order but
    finalisation happens via an explicit POST /payments/ call.  The payment
    must not be moved to SUCCESS prematurely.
    """
    user = User.objects.create_user(email="defer1@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=True, deferred=True)
    apply_provider_result(payment=payment, order=order, provider_result=result)

    payment.refresh_from_db()
    assert payment.status == Payment.Status.PENDING


@pytest.mark.django_db
def test_apply_result_deferred_leaves_order_created():
    """apply_provider_result(deferred=True) must leave order in CREATED state."""
    user = User.objects.create_user(email="defer2@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order, status=Payment.Status.PENDING, provider=Payment.Provider.DEV_FAKE
    )

    result = ProviderStartResult(success=True, deferred=True)
    apply_provider_result(payment=payment, order=order, provider_result=result)

    order.refresh_from_db()
    assert order.status == Order.Status.CREATED


@pytest.mark.django_db
def test_apply_result_deferred_creates_shipment_for_cod_order():
    user = User.objects.create_user(email="defer2-shipment@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        payment_method=Payment.PaymentMethod.COD,
        provider=Payment.Provider.DEV_FAKE,
    )

    result = ProviderStartResult(success=True, deferred=True)
    apply_provider_result(payment=payment, order=order, provider_result=result)

    order.refresh_from_db()
    shipment = Shipment.objects.get(order=order)

    assert shipment.status == ShipmentStatus.LABEL_CREATED
    assert order.status == Order.Status.CREATED


@pytest.mark.django_db
def test_apply_result_deferred_does_not_create_shipment_for_card_order():
    user = User.objects.create_user(email="defer2-card@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        payment_method=Payment.PaymentMethod.CARD,
        provider=Payment.Provider.ACQUIREMOCK,
    )

    result = ProviderStartResult(success=True, deferred=True)
    apply_provider_result(payment=payment, order=order, provider_result=result)

    assert Shipment.objects.filter(order=order).count() == 0


@pytest.mark.django_db
def test_orchestration_cod_without_simulated_result_creates_pending_payment():
    """COD checkout with no simulated_result → payment stays PENDING, order stays CREATED.

    This is the deferred DEV flow: checkout only initiates the payment, and
    the order is finalised via an explicit POST /payments/ call.
    """
    user = User.objects.create_user(email="defer3@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = PaymentOrchestrationService.start_payment(
        order=order,
        payment_method=Payment.PaymentMethod.COD,
        extra={},  # no simulated_result
    )

    assert payment.status == Payment.Status.PENDING, (
        "COD checkout without simulated_result must leave payment PENDING."
    )
    order.refresh_from_db()
    assert order.status == Order.Status.CREATED, (
        "COD checkout without simulated_result must leave order in CREATED state."
    )
    assert Shipment.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_orchestration_cod_with_explicit_success_pays_immediately():
    """COD with simulated_result='success' (via /payments/) → immediate SUCCESS + PAID.

    Explicit simulated_result bypasses the deferred path and finalises the
    payment synchronously, matching the legacy POST /payments/ dev flow.
    """
    user = User.objects.create_user(email="defer4@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = PaymentOrchestrationService.start_payment(
        order=order,
        payment_method=Payment.PaymentMethod.COD,
        extra={"simulated_result": "success"},
    )

    assert payment.status == Payment.Status.SUCCESS
    order.refresh_from_db()
    assert order.status == Order.Status.PAID
