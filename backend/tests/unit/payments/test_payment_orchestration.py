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
from django.utils import timezone

from api.exceptions.payment import OrderNotPayableException, PaymentAlreadyExistsException
from orders.models import Order
from orders.services.order_service import OrderService
from payments.models import Payment
from payments.providers.base import ProviderStartResult
from payments.providers.resolver import ProviderNotConfiguredException
from payments.services.payment_orchestration import PaymentOrchestrationService
from payments.services.payment_result_applier import apply_provider_result
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
def test_orchestration_raises_for_card_method():
    """start_payment raises ProviderNotConfiguredException for CARD (no provider yet)."""
    user = User.objects.create_user(email="orch4@example.com", password="pass")
    order = create_valid_order(user=user)

    with pytest.raises(ProviderNotConfiguredException):
        PaymentOrchestrationService.start_payment(
            order=order,
            payment_method=Payment.PaymentMethod.CARD,
            extra={},
        )


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
