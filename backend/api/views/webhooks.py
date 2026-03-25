"""Webhook ingress views.

This module contains views that receive inbound callbacks from external
payment providers.  Webhooks are public endpoints — authentication is done
exclusively via HMAC signature verification, not via session or JWT.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.providers.acquiremock_webhook import (
    parse_acquiremock_webhook,
    verify_acquiremock_signature,
)

logger = logging.getLogger(__name__)


class AcquireMockWebhookView(APIView):
    """Receive and verify inbound AcquireMock payment event webhooks.

    Authentication is via HMAC-SHA256 signature only — no session or JWT
    credentials are expected or accepted on this endpoint.

    Request:
        POST /api/v1/webhooks/acquiremock/
        Header: X-Signature: <hmac-sha256-hex>
        Body:   JSON with fields: payment_id, reference, amount, status, timestamp

    Responses:
        200  {"status": "received"}    — valid signature, payload accepted
        400  {"code": "...", ...}       — malformed or unparseable JSON body
        403  {"code": "...", ...}       — missing or invalid signature

    Idempotence, deduplication, and full business processing are out of scope
    for this slice and will be added in the next webhook processing slice.
    """

    # No session/JWT authentication — signature is the only auth mechanism.
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        # 1. Require the signature header before parsing the body.
        signature = request.META.get("HTTP_X_SIGNATURE")
        if not signature:
            logger.warning("AcquireMock webhook received without X-Signature header")
            return Response(
                {"code": "MISSING_SIGNATURE", "message": "Missing X-Signature header."},
                status=403,
            )

        # 2. Parse raw body — do not rely on DRF's pre-parsed request.data
        #    so we control exactly how the bytes are decoded.
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            logger.warning("AcquireMock webhook received with malformed JSON body")
            return Response(
                {"code": "MALFORMED_PAYLOAD", "message": "Request body is not valid JSON."},
                status=400,
            )

        # 3. Verify HMAC-SHA256 signature.
        secret = settings.ACQUIREMOCK_WEBHOOK_SECRET
        if not verify_acquiremock_signature(payload, signature, secret):
            logger.warning(
                "AcquireMock webhook rejected — signature mismatch "
                "(payment_id=%s)",
                payload.get("payment_id", "<unknown>"),
            )
            return Response(
                {"code": "INVALID_SIGNATURE", "message": "Webhook signature verification failed."},
                status=403,
            )

        # 4. Normalise payload into a typed event object.
        try:
            event = parse_acquiremock_webhook(payload)
        except ValueError as exc:
            logger.warning("AcquireMock webhook payload missing required field: %s", exc)
            return Response(
                {"code": "MALFORMED_PAYLOAD", "message": str(exc)},
                status=400,
            )

        # 5. Processing boundary — idempotent business logic goes here in the
        #    next slice (webhook processing / deduplication).
        logger.info(
            "AcquireMock webhook accepted: payment_id=%s status=%s",
            event.payment_id,
            event.status,
        )

        return Response({"status": "received"}, status=200)
