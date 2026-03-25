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
    canonical = json.dumps(payload, sort_keys=True)
    expected = hmac.new(
        key=secret.encode("utf-8"),
        msg=canonical.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
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
        status=str(data["status"]),
        timestamp=str(data["timestamp"]),
        raw=data,
    )
