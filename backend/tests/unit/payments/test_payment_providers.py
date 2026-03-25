"""Tests for payment provider abstraction layer (Slice 2).

Covers:
- Provider resolver behaviour
- DevFakeProvider contract and result shape
- Integration: existing fake flow intact after wiring
"""

import pytest
from django.contrib.auth import get_user_model

from payments.models import Payment
from payments.providers.base import PaymentStartContext, ProviderStartResult
from payments.providers.dev_fake import DevFakeProvider
from payments.providers.resolver import (
    ProviderNotConfiguredException,
    resolve_provider,
)
from orders.services.order_service import OrderService
from tests.conftest import create_valid_order

User = get_user_model()

# ---------------------------------------------------------------------------
# ProviderStartResult — shape and defaults
# ---------------------------------------------------------------------------


def test_provider_start_result_defaults():
    """ProviderStartResult has sensible defaults for optional fields."""
    result = ProviderStartResult(success=True)
    assert result.success is True
    assert result.provider_payment_id is None
    assert result.failure_reason is None
    assert result.redirect_url is None


def test_provider_start_result_failure_shape():
    """ProviderStartResult correctly carries failure data."""
    result = ProviderStartResult(success=False, failure_reason="Card declined")
    assert result.success is False
    assert result.failure_reason == "Card declined"
    assert result.redirect_url is None


# ---------------------------------------------------------------------------
# Provider resolver
# ---------------------------------------------------------------------------


def test_resolver_returns_dev_fake_provider_for_cod():
    """COD resolves to DevFakeProvider."""
    provider = resolve_provider(Payment.PaymentMethod.COD)
    assert isinstance(provider, DevFakeProvider)


def test_resolver_returns_dev_fake_provider_for_none():
    """None payment method (legacy / no method set) resolves to DevFakeProvider."""
    provider = resolve_provider(None)
    assert isinstance(provider, DevFakeProvider)


def test_resolver_raises_for_unknown_method():
    """Completely unknown method string raises ProviderNotConfiguredException."""
    with pytest.raises(ProviderNotConfiguredException):
        resolve_provider("WIRE_TRANSFER")


# ---------------------------------------------------------------------------
# DevFakeProvider
# ---------------------------------------------------------------------------


def test_dev_fake_provider_is_instance_of_base():
    """DevFakeProvider satisfies the BasePaymentProvider contract."""
    from payments.providers.base import BasePaymentProvider
    assert isinstance(DevFakeProvider(), BasePaymentProvider)


def test_dev_fake_provider_start_returns_success():
    """DevFakeProvider.start() returns success=True for simulated_result=success."""
    provider = DevFakeProvider()
    context = PaymentStartContext(order=None, payment=None, extra={"simulated_result": "success"})
    result = provider.start(context)
    assert isinstance(result, ProviderStartResult)
    assert result.success is True
    assert result.failure_reason is None


def test_dev_fake_provider_start_returns_failure():
    """DevFakeProvider.start() returns success=False for simulated_result=fail."""
    provider = DevFakeProvider()
    context = PaymentStartContext(order=None, payment=None, extra={"simulated_result": "fail"})
    result = provider.start(context)
    assert isinstance(result, ProviderStartResult)
    assert result.success is False
    assert result.failure_reason is not None
    assert len(result.failure_reason) > 0


def test_dev_fake_provider_defaults_to_success_when_no_result():
    """DevFakeProvider.start() defaults to success when simulated_result is absent."""
    provider = DevFakeProvider()
    context = PaymentStartContext(order=None, payment=None, extra={})
    result = provider.start(context)
    assert result.success is True


def test_dev_fake_provider_has_no_redirect_url():
    """DevFakeProvider never returns a redirect URL — it is a direct provider."""
    provider = DevFakeProvider()
    context = PaymentStartContext(order=None, payment=None, extra={"simulated_result": "success"})
    result = provider.start(context)
    assert result.redirect_url is None


# ---------------------------------------------------------------------------
# Integration: existing fake flow intact after wiring
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fake_flow_success_still_works_after_provider_wiring():
    """OrderService.create_payment_and_apply_result success path unchanged."""
    user = User.objects.create_user(email="prov1@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = OrderService.create_payment_and_apply_result(
        order=order, result="success", actor_user=user
    )

    assert payment.status == Payment.Status.SUCCESS
    assert payment.provider == Payment.Provider.DEV_FAKE
    assert payment.paid_at is not None
    assert payment.failed_at is None


@pytest.mark.django_db
def test_fake_flow_failure_still_works_after_provider_wiring():
    """OrderService.create_payment_and_apply_result failure path unchanged."""
    user = User.objects.create_user(email="prov2@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = OrderService.create_payment_and_apply_result(
        order=order, result="fail", actor_user=user
    )

    assert payment.status == Payment.Status.FAILED
    assert payment.provider == Payment.Provider.DEV_FAKE
    assert payment.failed_at is not None
    assert payment.failure_reason is not None
    assert payment.paid_at is None
