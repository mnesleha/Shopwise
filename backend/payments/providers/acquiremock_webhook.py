"""AcquireMock webhook signature verification and payload normalisation.

This module contains two responsibilities:

1. Signature verification — ``verify_acquiremock_signature()``
   Verifies the HMAC-SHA256 signature that AcquireMock attaches to every
   outbound webhook request via the ``X-Signature`` header.

2. Payload normalisation — ``parse_acquiremock_webhook()``
   Extracts and validates the documented AcquireMock webhook fields into a
   typed ``AcquireMockWebhookEvent`` dataclass, providing a clean boundary
   between raw HTTP ingress and downstream business processing.

Signing scheme (as per AcquireMock documentation):
  - Algorithm:  HMAC-SHA256
  - Message:    json.dumps(payload, sort_keys=True).encode("utf-8")
  - Key:        ACQUIREMOCK_WEBHOOK_SECRET.encode("utf-8")
  - Comparison: hmac.compare_digest (constant-time)
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def _compute_hmac_sha256_hex(message: bytes, secret: str) -> str:
    """Return hex-encoded HMAC-SHA256 for *message* using *secret*."""
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=message,
        digestmod=hashlib.sha256,
    ).hexdigest()


def compute_acquiremock_signature(payload: dict, secret: str) -> str:
    """Return AcquireMock's documented signature for *payload*."""
    canonical = json.dumps(payload, sort_keys=True).encode("utf-8")
    return _compute_hmac_sha256_hex(canonical, secret)


def describe_acquiremock_signature_mismatch(
    payload: dict,
    signature: str,
    secret: str,
    raw_body: bytes,
) -> dict[str, Any]:
    """Return safe diagnostics for investigating webhook signature mismatches.

    The returned metadata intentionally excludes the secret itself, the expected
    signature, and the raw payload contents. It is designed to distinguish the
    most likely failure modes:

    - stale / wrong secret
    - malformed signature header
    - provider signing the raw JSON body instead of canonical sort_keys JSON
    """
    signature = signature.strip()
    canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    raw_body_signature = _compute_hmac_sha256_hex(raw_body, secret)

    return {
        "signature_len": len(signature),
        "signature_is_hex": len(signature) == 64 and all(
            ch in "0123456789abcdefABCDEF" for ch in signature
        ),
        "matches_raw_body": hmac.compare_digest(raw_body_signature, signature),
        "secret_fingerprint": hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12],
        "canonical_payload_fingerprint": hashlib.sha256(canonical_bytes).hexdigest()[:12],
        "raw_body_fingerprint": hashlib.sha256(raw_body).hexdigest()[:12],
    }


def verify_acquiremock_signature(payload: dict, signature: str, secret: str) -> bool:
    """Return True if *signature* is the valid HMAC-SHA256 of *payload*.

    The canonical message is ``json.dumps(payload, sort_keys=True)`` encoded
    as UTF-8.  Comparison is constant-time via :func:`hmac.compare_digest` to
    prevent timing-oracle attacks.

    Args:
        payload:   The parsed JSON payload dict received from AcquireMock.
        signature: The hex-encoded HMAC sent in the ``X-Signature`` header.
        secret:    The shared webhook secret (``ACQUIREMOCK_WEBHOOK_SECRET``).

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    expected = compute_acquiremock_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Payload normalisation
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = ("payment_id", "reference", "amount", "status", "timestamp")


@dataclass
class AcquireMockWebhookEvent:
    """Normalised representation of a single AcquireMock webhook event.

    All string fields are coerced to ``str`` at parse time so downstream
    code can rely on a consistent type regardless of JSON encoding quirks.

    Attributes:
        payment_id:  AcquireMock's unique identifier for the payment session.
        reference:   Order-level reference echoed back by AcquireMock.
        amount:      Amount in the invoice currency, as a string (e.g. "99.99").
        status:      Payment outcome reported by AcquireMock (e.g. "PAID", "FAILED").
        timestamp:   ISO-8601 event timestamp from AcquireMock.
        raw:         Original payload dict kept for audit and debug purposes.
    """

    payment_id: str
    reference: str
    amount: str
    status: str
    timestamp: str
    raw: dict = field(repr=False)


def parse_acquiremock_webhook(data: dict) -> AcquireMockWebhookEvent:
    """Parse and normalise an AcquireMock webhook payload.

    Args:
        data: The parsed JSON dict from the webhook request body.

    Returns:
        An :class:`AcquireMockWebhookEvent` with all required fields populated.

    Raises:
        ValueError: If any required field is absent from *data*.
    """
    for field_name in _REQUIRED_FIELDS:
        if field_name not in data:
            raise ValueError(
                f"AcquireMock webhook payload missing required field: '{field_name}'"
            )

    return AcquireMockWebhookEvent(
        payment_id=str(data["payment_id"]),
        reference=str(data["reference"]),
        amount=str(data["amount"]),
        status=str(data["status"]).strip().upper(),
        timestamp=str(data["timestamp"]),
        raw=data,
    )
