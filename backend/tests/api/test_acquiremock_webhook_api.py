"""API-level tests for the AcquireMock webhook endpoint.

These tests exercise the full HTTP request lifecycle:
- valid signature is accepted
- invalid signature is rejected (403)
- missing signature is rejected (403)
- malformed JSON is rejected (400)
- verified payload reaches the normalisation boundary

No idempotence logic is tested here — that belongs to a future slice.
No running AcquireMock server is required; signing is done inline.
"""

import hashlib
import hmac
import json

import pytest
from rest_framework.test import APIClient

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


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_valid_signature_is_accepted(anon_client, settings):
    """A correctly signed webhook payload returns 200 OK."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
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
    """A valid webhook triggers the normalisation handler (no side effects tested yet).

    This test verifies the happy path reaches the processing boundary — the
    actual idempotent business logic is out of scope for this slice.
    """
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    sig = _sign(SAMPLE_PAYLOAD, _TEST_SECRET)

    # Verify no exception is raised and the endpoint returns 200.
    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(SAMPLE_PAYLOAD),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_webhook_with_all_required_fields_is_accepted(anon_client, settings):
    """Webhook with all documented AcquireMock fields is accepted."""
    settings.ACQUIREMOCK_WEBHOOK_SECRET = _TEST_SECRET
    payload = {
        "payment_id": "pay_999",
        "reference": "ref_123abc",
        "amount": "250.00",
        "status": "FAILED",
        "timestamp": "2026-03-25T12:30:00Z",
    }
    sig = _sign(payload, _TEST_SECRET)

    response = anon_client.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
    )

    assert response.status_code == 200
