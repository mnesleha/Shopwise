"""Tests for AcquireMockProvider (Slice PR2/1).

Covers:
- AcquireMockProvider satisfies the BasePaymentProvider contract.
- Successful API response mapped to ProviderStartResult with redirect_url.
- provider_payment_id derived from the hosted page URL.
- Malformed response (missing required fields) yields explicit failure.
- Non-2xx HTTP response yields explicit failure with status code in reason.
- Network error (requests.RequestException) yields explicit failure.
- Provider does NOT mutate the order or payment objects.
- Resolver now maps CARD to AcquireMockProvider.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from payments.models import Payment
from payments.providers.acquiremock import AcquireMockProvider
from payments.providers.base import BasePaymentProvider, PaymentStartContext, ProviderStartResult
from payments.providers.resolver import resolve_provider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_BASE_URL = "https://acquiremock.test"
FAKE_API_KEY = "test-key-abc123"
FAKE_PUBLIC_BASE_URL = "https://shopwise-backend.test"


def _make_context(
    *,
    order_id="order-42",
    amount="25.00",
    currency="USD",
    callback_base_url=None,
    return_url="https://shop.test/return",
    webhook_url="https://api.shop.test/api/v1/webhooks/acquiremock/",
):
    """Build a minimal PaymentStartContext with enough data for AcquireMock."""
    order = MagicMock()
    order.id = order_id

    payment = MagicMock()
    payment.amount = amount
    payment.currency = currency

    return PaymentStartContext(
        order=order,
        payment=payment,
        extra={
            "callback_base_url": callback_base_url,
            "return_url": return_url,
            "webhook_url": webhook_url,
        },
    )


def _ok_response(page_url="https://acquiremock.test/checkout/pay_111"):
    """Returns a mock requests.Response with a successful AcquireMock payload."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {"pageUrl": page_url}
    return mock_resp


# ---------------------------------------------------------------------------
# Contract: is a BasePaymentProvider
# ---------------------------------------------------------------------------


def test_acquiremock_provider_is_instance_of_base():
    """AcquireMockProvider satisfies the BasePaymentProvider contract."""
    with patch("payments.providers.acquiremock.settings") as mock_settings:
        mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
        mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
        mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
        provider = AcquireMockProvider()
    assert isinstance(provider, BasePaymentProvider)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_returns_success_with_redirect_url(mock_settings, mock_post):
    """Successful API response maps to ProviderStartResult(success=True, redirect_url=...)."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10
    mock_post.return_value = _ok_response()

    provider = AcquireMockProvider()
    result = provider.start(_make_context())

    assert isinstance(result, ProviderStartResult)
    assert result.success is True
    assert result.redirect_url == "https://acquiremock.test/checkout/pay_111"
    assert result.failure_reason is None


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_propagates_provider_payment_id(mock_settings, mock_post):
    """The provider_payment_id is derived from the hosted pageUrl."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10
    mock_post.return_value = _ok_response(page_url="https://acquiremock.test/checkout/pay_xyz_999")

    provider = AcquireMockProvider()
    result = provider.start(_make_context())

    assert result.provider_payment_id == "pay_xyz_999"


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_sends_correct_request_body(mock_settings, mock_post):
    """Provider POSTs the expected fields to AcquireMock."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10
    mock_post.return_value = _ok_response()

    context = _make_context(
        order_id="order-77",
        amount="50.00",
        currency="EUR",
        return_url="https://shop.test/ok",
        webhook_url="https://api.shop.test/api/v1/webhooks/acquiremock/",
    )
    AcquireMockProvider().start(context)

    _, kwargs = mock_post.call_args
    body = kwargs["json"]
    assert body["reference"] == "order-77"
    assert body["amount"] == 5000
    assert body["webhookUrl"] == "https://api.shop.test/api/v1/webhooks/acquiremock/"
    assert body["redirectUrl"] == "https://shop.test/ok"
    assert mock_post.call_args.args[0] == "https://acquiremock.test/api/create-invoice"


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_composes_callback_urls_from_generic_base_context(mock_settings, mock_post):
    """Hosted callback URL composition belongs to the payments layer, not checkout."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.FRONTEND_RETURN_URL = "https://shop.test/return-from-settings"
    mock_settings.ACQUIREMOCK_TIMEOUT = 10
    mock_post.return_value = _ok_response()

    context = _make_context(
        callback_base_url="https://api.shop.test/",
        return_url=None,
        webhook_url=None,
    )
    AcquireMockProvider().start(context)

    _, kwargs = mock_post.call_args
    body = kwargs["json"]
    assert body["redirectUrl"] == "https://shop.test/return-from-settings"
    assert body["webhookUrl"] == "https://api.shop.test/api/v1/webhooks/acquiremock/"


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_sends_api_key_header(mock_settings, mock_post):
    """Provider sends the X-Api-Key header with every request."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = "secret-key-here"
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10
    mock_post.return_value = _ok_response()

    AcquireMockProvider().start(_make_context())

    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["X-Api-Key"] == "secret-key-here"


# ---------------------------------------------------------------------------
# Failure paths: malformed responses
# ---------------------------------------------------------------------------


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_fails_when_response_missing_redirect_url(mock_settings, mock_post):
    """Missing pageUrl in response yields success=False."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {"reference": "pay_abc"}  # no pageUrl
    mock_post.return_value = mock_resp

    result = AcquireMockProvider().start(_make_context())

    assert result.success is False
    assert result.failure_reason is not None
    assert len(result.failure_reason) > 0


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_fails_when_page_url_has_no_payment_id(mock_settings, mock_post):
    """A pageUrl without an embedded payment id yields success=False."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {"pageUrl": "https://acquiremock.test/"}
    mock_post.return_value = mock_resp

    result = AcquireMockProvider().start(_make_context())

    assert result.success is False
    assert result.failure_reason is not None


# ---------------------------------------------------------------------------
# Failure paths: HTTP errors
# ---------------------------------------------------------------------------


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_fails_on_4xx_response(mock_settings, mock_post):
    """Non-2xx response (4xx) yields success=False with HTTP status in reason."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10

    mock_resp = MagicMock()
    mock_resp.status_code = 422
    mock_resp.ok = False
    mock_resp.json.return_value = {"error": "Invalid order"}
    mock_post.return_value = mock_resp

    result = AcquireMockProvider().start(_make_context())

    assert result.success is False
    assert result.failure_reason is not None
    assert "422" in result.failure_reason


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_fails_on_5xx_response(mock_settings, mock_post):
    """Non-2xx response (5xx) yields success=False."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10

    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.ok = False
    mock_resp.json.return_value = {}
    mock_post.return_value = mock_resp

    result = AcquireMockProvider().start(_make_context())

    assert result.success is False
    assert result.failure_reason is not None
    assert "503" in result.failure_reason


# ---------------------------------------------------------------------------
# Failure paths: network errors
# ---------------------------------------------------------------------------


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_start_fails_on_network_error(mock_settings, mock_post):
    """requests.RequestException (e.g. timeout, connection error) yields success=False."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10
    mock_post.side_effect = requests.RequestException("Connection timed out")

    result = AcquireMockProvider().start(_make_context())

    assert result.success is False
    assert result.failure_reason is not None
    assert len(result.failure_reason) > 0


# ---------------------------------------------------------------------------
# Immutability guard
# ---------------------------------------------------------------------------


@patch("payments.providers.acquiremock.requests.post")
@patch("payments.providers.acquiremock.settings")
def test_provider_does_not_mutate_order_or_payment(mock_settings, mock_post):
    """AcquireMockProvider must not call any mutating methods on order or payment."""
    mock_settings.ACQUIREMOCK_BASE_URL = FAKE_BASE_URL
    mock_settings.ACQUIREMOCK_API_KEY = FAKE_API_KEY
    mock_settings.PUBLIC_BASE_URL = FAKE_PUBLIC_BASE_URL
    mock_settings.ACQUIREMOCK_TIMEOUT = 10
    mock_post.return_value = _ok_response()

    order = MagicMock()
    payment = MagicMock()
    context = PaymentStartContext(order=order, payment=payment, extra={"return_url": "https://test/"})

    AcquireMockProvider().start(context)

    order.save.assert_not_called()
    payment.save.assert_not_called()


# ---------------------------------------------------------------------------
# Resolver: CARD now maps to AcquireMockProvider
# ---------------------------------------------------------------------------


def test_resolver_returns_acquiremock_for_card():
    """CARD resolves to AcquireMockProvider after wiring."""
    provider = resolve_provider(Payment.PaymentMethod.CARD)
    assert isinstance(provider, AcquireMockProvider)
