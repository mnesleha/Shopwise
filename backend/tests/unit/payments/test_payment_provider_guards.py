"""Unit tests for payment provider guards and explicitness invariants.

Covers the corrective fixes introduced in PR2 follow-up:

1. Provider enum is explicit — DevFakeProvider and AcquireMockProvider each
   expose a stable ``provider_enum`` class attribute; no class-name fallback.
2. AcquireMock fails closed when ACQUIREMOCK_BASE_URL is missing.
3. AcquireMock fails closed when ACQUIREMOCK_API_KEY is missing.
4. AcquireMock fails explicitly when payment.amount is None
    (hosted providers require a financial snapshot to create a session).
5. DevFake / COD flow is not affected by the hosted-provider guards.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from orders.models import Order
from payments.models import Payment
from payments.providers.acquiremock import AcquireMockProvider
from payments.providers.base import PaymentStartContext, ProviderStartResult
from payments.providers.dev_fake import DevFakeProvider
from tests.conftest import create_valid_order

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# 1. Provider enum is explicit
# ---------------------------------------------------------------------------


def test_dev_fake_provider_has_explicit_provider_enum():
    """DevFakeProvider exposes provider_enum == DEV_FAKE (not derived from class name)."""
    assert hasattr(DevFakeProvider, "provider_enum"), (
        "DevFakeProvider must declare a provider_enum class attribute."
    )
    assert DevFakeProvider.provider_enum == Payment.Provider.DEV_FAKE


def test_acquiremock_provider_has_explicit_provider_enum():
    """AcquireMockProvider exposes provider_enum == ACQUIREMOCK (not derived from class name)."""
    assert hasattr(AcquireMockProvider, "provider_enum"), (
        "AcquireMockProvider must declare a provider_enum class attribute."
    )
    assert AcquireMockProvider.provider_enum == Payment.Provider.ACQUIREMOCK


def test_provider_enum_is_accessible_on_instance():
    """provider_enum is accessible on an instance as well as on the class."""
    dev = DevFakeProvider()
    acq = AcquireMockProvider()
    assert dev.provider_enum == Payment.Provider.DEV_FAKE
    assert acq.provider_enum == Payment.Provider.ACQUIREMOCK


# ---------------------------------------------------------------------------
# 2. AcquireMock fails closed — missing ACQUIREMOCK_BASE_URL
# ---------------------------------------------------------------------------


def _make_context(amount="50.00", currency="USD") -> PaymentStartContext:
    """Return a minimal PaymentStartContext for AcquireMock unit tests."""
    user = User.objects.create_user(
        email="acq_guard@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = MagicMock()
    payment.amount = amount
    payment.currency = currency
    return PaymentStartContext(
        order=order,
        payment=payment,
        extra={
            "return_url": "https://example.test/return",
            "webhook_url": "https://api.example.test/api/v1/webhooks/acquiremock/",
        },
    )


def test_missing_base_url_returns_failure(settings):
    """AcquireMock returns ProviderStartResult(success=False) when BASE_URL is empty."""
    settings.ACQUIREMOCK_BASE_URL = ""
    settings.ACQUIREMOCK_API_KEY = "some-key"
    provider = AcquireMockProvider()
    result = provider.start(_make_context())
    assert isinstance(result, ProviderStartResult)
    assert result.success is False
    assert result.failure_reason  # must contain a human-readable message
    assert "ACQUIREMOCK_BASE_URL" in result.failure_reason


def test_missing_base_url_does_not_make_network_call(settings):
    """When BASE_URL is empty, no HTTP call is attempted."""
    settings.ACQUIREMOCK_BASE_URL = ""
    settings.ACQUIREMOCK_API_KEY = "some-key"
    with patch("payments.providers.acquiremock.requests.post") as post_mock:
        AcquireMockProvider().start(_make_context())
    post_mock.assert_not_called()


# ---------------------------------------------------------------------------
# 3. AcquireMock fails closed — missing ACQUIREMOCK_API_KEY
# ---------------------------------------------------------------------------


def test_missing_api_key_returns_failure(settings):
    """AcquireMock returns ProviderStartResult(success=False) when API_KEY is empty."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = ""
    provider = AcquireMockProvider()
    result = provider.start(_make_context())
    assert result.success is False
    assert result.failure_reason
    assert "ACQUIREMOCK_API_KEY" in result.failure_reason


def test_missing_api_key_does_not_make_network_call(settings):
    """When API_KEY is empty, no HTTP call is attempted."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = ""
    with patch("payments.providers.acquiremock.requests.post") as post_mock:
        AcquireMockProvider().start(_make_context())
    post_mock.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Hosted provider financial snapshot validation
# ---------------------------------------------------------------------------


def test_acquiremock_fails_when_amount_is_none(settings):
    """AcquireMock returns failure when payment.amount is None."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "key"
    result = AcquireMockProvider().start(_make_context(amount=None))
    assert result.success is False
    assert result.failure_reason


def test_acquiremock_fails_when_currency_is_none(settings):
    """AcquireMock still starts when payment.currency is None."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "key"
    with patch("payments.providers.acquiremock.requests.post") as post_mock:
        post_mock.return_value.ok = True
        post_mock.return_value.status_code = 200
        post_mock.return_value.json.return_value = {
            "pageUrl": "https://acquiremock.test/checkout/pay_curr_none"
        }
        result = AcquireMockProvider().start(_make_context(currency=None))
    assert result.success is True
    assert result.provider_payment_id == "pay_curr_none"


def test_acquiremock_none_amount_does_not_make_network_call(settings):
    """Missing amount prevents any HTTP call to AcquireMock."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "key"
    with patch("payments.providers.acquiremock.requests.post") as post_mock:
        AcquireMockProvider().start(_make_context(amount=None))
    post_mock.assert_not_called()


# ---------------------------------------------------------------------------
# 5. DevFake / COD is not affected by hosted-provider guards
# ---------------------------------------------------------------------------


def test_dev_fake_success_unaffected(settings):
    """DevFake succeeds normally — COD guard logic must not interfere."""
    user = User.objects.create_user(email="devfake_g@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = MagicMock()
    payment.amount = None   # deliberately None — DevFake must not care
    payment.currency = None
    ctx = PaymentStartContext(order=order, payment=payment, extra={})
    result = DevFakeProvider().start(ctx)
    assert result.success is True


def test_dev_fake_failure_unaffected(settings):
    """DevFake failure path unaffected by provider guard changes."""
    user = User.objects.create_user(email="devfake_gf@example.com", password="pass")
    order = create_valid_order(user=user)
    payment = MagicMock()
    payment.amount = None
    payment.currency = None
    ctx = PaymentStartContext(order=order, payment=payment, extra={"simulated_result": "fail"})
    result = DevFakeProvider().start(ctx)
    assert result.success is False
