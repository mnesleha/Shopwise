"""Unit tests for the AcquireMock webhook signature helper and payload normaliser.

These tests verify the low-level helper functions in isolation, without
making real HTTP requests or touching the database.
"""

import hashlib
import hmac
import json

import pytest

from payments.providers.acquiremock_webhook import (
    AcquireMockWebhookEvent,
    parse_acquiremock_webhook,
    verify_acquiremock_signature,
)

_SECRET = "unit-test-secret-xyz"


def _make_sig(payload: dict, secret: str) -> str:
    canonical = json.dumps(payload, sort_keys=True)
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=canonical.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


SAMPLE = {
    "payment_id": "pay_abc",
    "reference": "ref_001",
    "amount": "49.95",
    "status": "PAID",
    "timestamp": "2026-03-25T09:00:00Z",
}


# ---------------------------------------------------------------------------
# verify_acquiremock_signature
# ---------------------------------------------------------------------------


def test_signature_helper_accepts_valid_signature():
    """Correct HMAC-SHA256 signature is accepted."""
    sig = _make_sig(SAMPLE, _SECRET)
    assert verify_acquiremock_signature(SAMPLE, sig, _SECRET) is True


def test_signature_helper_rejects_wrong_signature():
    """A tampered signature string is rejected."""
    assert verify_acquiremock_signature(SAMPLE, "badhex0000000000", _SECRET) is False


def test_signature_helper_rejects_wrong_secret():
    """Signature computed with a different secret is rejected."""
    sig = _make_sig(SAMPLE, "other-secret")
    assert verify_acquiremock_signature(SAMPLE, sig, _SECRET) is False


def test_signature_helper_uses_sort_keys_canonicalisation():
    """Key ordering does not matter — canonical form is always sort_keys=True.

    This test verifies that the helper re-canonicalises the payload rather
    than signing whatever order keys arrive in.
    """
    shuffled = {
        "timestamp": SAMPLE["timestamp"],
        "status": SAMPLE["status"],
        "reference": SAMPLE["reference"],
        "payment_id": SAMPLE["payment_id"],
        "amount": SAMPLE["amount"],
    }
    sig = _make_sig(SAMPLE, _SECRET)
    # shuffled dict with the same values but different insertion order
    # should verify against the same signature because sort_keys=True is used.
    assert verify_acquiremock_signature(shuffled, sig, _SECRET) is True


def test_signature_helper_rejects_tampered_payload():
    """Modifying any payload field invalidates the signature."""
    sig = _make_sig(SAMPLE, _SECRET)
    tampered = {**SAMPLE, "amount": "1.00"}  # amount changed
    assert verify_acquiremock_signature(tampered, sig, _SECRET) is False


def test_signature_helper_rejects_empty_string_signature():
    """Empty string is rejected (not silently accepted)."""
    assert verify_acquiremock_signature(SAMPLE, "", _SECRET) is False


def test_signature_helper_uses_hmac_compare_digest():
    """Verification result is bool, not an exception for mismatches."""
    result = verify_acquiremock_signature(SAMPLE, "x" * 64, _SECRET)
    assert isinstance(result, bool)
    assert result is False


# ---------------------------------------------------------------------------
# parse_acquiremock_webhook
# ---------------------------------------------------------------------------


def test_parse_returns_acquiremock_webhook_event():
    """parse_acquiremock_webhook returns an AcquireMockWebhookEvent."""
    event = parse_acquiremock_webhook(SAMPLE)
    assert isinstance(event, AcquireMockWebhookEvent)


def test_parse_maps_all_required_fields():
    """All required payload fields are mapped correctly."""
    event = parse_acquiremock_webhook(SAMPLE)
    assert event.payment_id == "pay_abc"
    assert event.reference == "ref_001"
    assert event.amount == "49.95"
    assert event.status == "PAID"
    assert event.timestamp == "2026-03-25T09:00:00Z"


def test_parse_preserves_raw_payload():
    """The original dict is preserved in the raw field for audit/debug."""
    event = parse_acquiremock_webhook(SAMPLE)
    assert event.raw == SAMPLE


def test_parse_raises_on_missing_required_field():
    """Missing required field raises ValueError with a descriptive message."""
    incomplete = {k: v for k, v in SAMPLE.items() if k != "payment_id"}
    with pytest.raises(ValueError, match="payment_id"):
        parse_acquiremock_webhook(incomplete)


def test_parse_raises_on_missing_status_field():
    """Missing 'status' field raises ValueError."""
    incomplete = {k: v for k, v in SAMPLE.items() if k != "status"}
    with pytest.raises(ValueError, match="status"):
        parse_acquiremock_webhook(incomplete)


def test_parse_coerces_fields_to_strings():
    """Numeric fields (e.g. amount as float) are coerced to strings."""
    data = {**SAMPLE, "amount": 99.5}  # float instead of string
    event = parse_acquiremock_webhook(data)
    assert event.amount == "99.5"
