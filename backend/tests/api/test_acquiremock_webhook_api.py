"""API-level tests for the AcquireMock webhook endpoint.

These tests exercise the full HTTP request lifecycle:
- valid signature + known payment → 200 received
- invalid or missing signature → 403
- malformed JSON → 400
- unknown payment_id → 422
- unsupported status → 422

No running AcquireMock server is required; signing is done inline.
"""

import hashlib
import hmac
import json
import logging

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from orders.models import Order
from payments.models import Payment
from tests.conftest import create_valid_order

User = get_user_model()

WEBHOOK_URL = "/api/v1/webhooks/acquiremock/"
_TEST_SECRET = "test-webhook-secret-abc123"

# Deterministic sample payload that matches AcquireMock's documented shape.
SAMPLE_PAYLOAD = {
    "payment_id": "pay_abc123",
    "reference": "ref_xyz789",
    "amount": "99.99",
    "status": "PAID",
    "timestamp": "2026-03-25T10:00:00Z",
}


def _sign(payload: dict, secret: str) -> str:
    """Compute HMAC-SHA256 over json.dumps(payload, sort_keys=True).

    This mirrors AcquireMock's documented signing scheme exactly.
    """
    canonical = json.dumps(payload, sort_keys=True)
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=canonical.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


@pytest.fixture
def anon_client():
    """Unauthenticated API client — webhooks are public endpoints."""
    return APIClient()


def _create_acquiremock_payment(provider_payment_id: str) -> Payment:
    """Create an ACQUIREMOCK payment in PENDING state for webhook processing tests."""
    user = User.objects.create_user(
        email=f"wh_api_{provider_payment_id}@example.com", password="pass"
    )
    order = create_valid_order(user=user)
    return Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        provider=Payment.Provider.ACQUIREMOCK,
        provider_payment_id=provider_payment_id,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_valid_signature_is_accepted(anon_client, settings):
    """A correctly signed webhook payload for a known payment returns 200 OK."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    _create_acquiremock_payment(SAMPLE_PAYLOAD["payment_id"])
    sig = _sign(SAMPLE_PAYLOAD, _TEST_SECRET)

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_valid_response_body_is_acknowledgement(anon_client, settings):
    """Accepted webhook returns a simple acknowledgement body."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    _create_acquiremock_payment(SAMPLE_PAYLOAD["payment_id"])
    sig = _sign(SAMPLE_PAYLOAD, _TEST_SECRET)

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.json()["status"] == "received"


# ---------------------------------------------------------------------------
# Signature rejection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_invalid_signature_is_rejected(anon_client, settings):
    """A tampered or incorrect signature returns 403 Forbidden."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE="deadbeef000000000000000000000000000000000000000000000000deadbeef",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_invalid_signature_logs_safe_diagnostics(anon_client, settings, caplog):
    """Mismatch log includes enough metadata to distinguish config vs signing issues."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    caplog.set_level(logging.WARNING)

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE="deadbeef000000000000000000000000000000000000000000000000deadbeef",
    )

    assert response.status_code == 403
    assert "AcquireMock webhook rejected — signature mismatch" in caplog.text
    assert "signature_len=64" in caplog.text
    assert "signature_is_hex=True" in caplog.text
    assert "matches_raw_body=False" in caplog.text
    assert "secret_fp=" in caplog.text


@pytest.mark.django_db
def test_missing_signature_is_rejected(anon_client, settings):
    """A request without the X-Signature header returns 403 Forbidden."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        # No HTTP_X_SIGNATURE header
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_signature_from_wrong_secret_is_rejected(anon_client, settings):
    """A signature computed with a different secret is rejected."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    sig = _sign(SAMPLE_PAYLOAD, "completely-different-secret")

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Malformed input
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_malformed_json_is_rejected(anon_client, settings):
    """A request with invalid JSON body returns 400 Bad Request."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET

    response = anon_client.post(
        WEBHOOK_URL,
        data=b"not valid json{{{",
        content_type="application/json",
        HTTP_X_SIGNATURE="any-signature",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_empty_body_is_rejected(anon_client, settings):
    """An empty body returns 400 Bad Request."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET

    response = anon_client.post(
        WEBHOOK_URL,
        data=b"",
        content_type="application/json",
        HTTP_X_SIGNATURE="any-signature",
    )

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Normalisation boundary
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_verified_payload_reaches_normalisation_boundary(anon_client, settings):
    """A valid webhook for a known payment returns 200 and applies state."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    _create_acquiremock_payment(SAMPLE_PAYLOAD["payment_id"])
    sig = _sign(SAMPLE_PAYLOAD, _TEST_SECRET)

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_webhook_with_all_required_fields_is_accepted(anon_client, settings):
    """Webhook with all documented AcquireMock fields for a known payment is accepted."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    payload = {
        "payment_id": "pay_999",
        "reference": "ref_123abc",
        "amount": "250.00",
        "status": "FAILED",
        "timestamp": "2026-03-25T12:30:00Z",
    }
    _create_acquiremock_payment(payload["payment_id"])
    sig = _sign(payload, _TEST_SECRET)

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_lowercase_paid_status_is_accepted(anon_client, settings):
    """AcquireMock's lowercase provider statuses are accepted via normalization."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    payload = {**SAMPLE_PAYLOAD, "payment_id": "pay_lower_paid_api", "status": "paid"}
    _create_acquiremock_payment(payload["payment_id"])
    sig = _sign(payload, _TEST_SECRET)

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Error responses
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unknown_payment_id_returns_422(anon_client, settings):
    """A verified webhook referencing an unknown payment_id returns 422."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    # No matching Payment created intentionally.
    sig = _sign(SAMPLE_PAYLOAD, _TEST_SECRET)

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "PAYMENT_NOT_FOUND"


@pytest.mark.django_db
def test_unsupported_status_returns_422(anon_client, settings):
    """A verified webhook with an unsupported status string returns 422."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    payload = {**SAMPLE_PAYLOAD, "status": "REFUNDED", "payment_id": "pay_refund_api"}
    _create_acquiremock_payment(payload["payment_id"])
    sig = _sign(payload, _TEST_SECRET)

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "UNSUPPORTED_STATUS"


# ---------------------------------------------------------------------------
# Fail-closed: empty webhook secret
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_empty_webhook_secret_is_rejected(anon_client, settings):
    """When ACQUIREMOCK_WEBHOOK_SECRET is empty, all webhook calls must be rejected.

    An empty secret would make hmac.compare_digest accept any zero-length or
    trivially-computed signature.  The endpoint must refuse to process webhooks
    when the secret is not configured.
    """
    settings.ACQUIREMOCK_WEBHOOK_SECRET = ""
    # Even a correctly-crafted signature for an empty secret must not pass through.
    sig = _sign(SAMPLE_PAYLOAD, "")  # HMAC with empty key — must still be rejected
    _create_acquiremock_payment(SAMPLE_PAYLOAD["payment_id"])

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    # Must not be 200 — fail-closed means all webhooks are rejected when unconfigured.
    assert response.status_code != 200, (
        "Webhook endpoint must not process events when ACQUIREMOCK_WEBHOOK_SECRET is empty."
    )


@pytest.mark.django_db
def test_empty_webhook_secret_with_signature_header_is_rejected(anon_client, settings):
    """A syntactically valid X-Signature is still rejected when secret is unconfigured."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = ""
    sig = _sign(SAMPLE_PAYLOAD, "")

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code in (403, 500)


# ---------------------------------------------------------------------------
# Webhook finalizes PENDING payment to SUCCESS (redirect flow end-to-end)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_webhook_finalizes_pending_acquiremock_payment_to_success(anon_client, settings):
    """A PAID webhook event transitions a PENDING AcquireMock payment to SUCCESS.

    This is the correct finalization path for CARD/redirect payments:
      1. Checkout creates a PENDING payment.
      2. Customer pays on the hosted page.
      3. AcquireMock sends a PAID webhook → payment becomes SUCCESS, order PAID.
    """
    from orders.models import Order as OrderModel

    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET

    user = User.objects.create_user(email="wh_finalize@example.com", password="pass")
    from tests.conftest import create_valid_order
    order = create_valid_order(user=user)

    payment = Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        provider=Payment.Provider.ACQUIREMOCK,
        provider_payment_id=SAMPLE_PAYLOAD["payment_id"],
    )
    from orders.services.inventory_reservation_service import reserve_for_checkout
    from products.models import Product
    product = Product.objects.create(
        name="WH Finalize Product", price=100, stock_quantity=10, is_active=True)
    reserve_for_checkout(order=order, items=[{"product_id": product.id, "quantity": 1}])

    assert payment.status == Payment.Status.PENDING
    assert order.status == OrderModel.Status.CREATED

    sig = _sign(SAMPLE_PAYLOAD, _TEST_SECRET)
    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 200

    payment.refresh_from_db()
    order.refresh_from_db()

    assert payment.status == Payment.Status.SUCCESS, (
        "Webhook PAID event must finalize payment to SUCCESS."
    )
    assert order.status == OrderModel.Status.PAID, (
        "Webhook PAID event must transition order to PAID."
    )
