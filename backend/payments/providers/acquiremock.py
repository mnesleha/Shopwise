"""AcquireMock payment provider.

Integrates with the AcquireMock hosted mock gateway to create a payment
session and return a redirect URL for the customer.

AcquireMock mirrors the redirect flow of real hosted card PSPs:
  1. Backend POSTs an invoice-creation request to AcquireMock.
  2. AcquireMock responds with a ``redirect_url`` and an external payment ``id``.
  3. The frontend redirects the customer to the hosted payment page.
  4. The customer completes payment on that page.
  5. AcquireMock posts a webhook back to our backend to confirm the result.
     (Webhook handling is a separate future slice — not part of this provider.)

Configuration (read from Django settings):
  ACQUIREMOCK_BASE_URL  — base URL of the AcquireMock server (no trailing slash).
  ACQUIREMOCK_API_KEY   — token sent as "X-Api-Key" on every outbound request.
  ACQUIREMOCK_TIMEOUT   — HTTP timeout in seconds (default: 10).

This provider must NOT mutate order or payment objects — that responsibility
belongs exclusively to the payment result applier.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from payments.models import Payment
from payments.providers.base import BasePaymentProvider, PaymentStartContext, ProviderStartResult

logger = logging.getLogger(__name__)

_CREATE_INVOICE_PATH = "/api/invoices"


class AcquireMockProvider(BasePaymentProvider):
    """Hosted-gateway provider backed by the AcquireMock service.

    Sends a create-invoice request and returns a :class:`ProviderStartResult`
    containing the redirect URL for the customer and the external payment id.

    On any error (HTTP non-2xx, malformed response, or network failure) returns
    ``ProviderStartResult(success=False, ...)`` — never raises.
    """

    #: Stable provider enum value — used by orchestration to set Payment.provider.
    provider_enum = Payment.Provider.ACQUIREMOCK

    def start(self, context: PaymentStartContext) -> ProviderStartResult:
        """Send an invoice-creation request to AcquireMock.

        Args:
            context: Must include ``context.extra["return_url"]`` — the URL
                     AcquireMock will redirect the customer to after payment.

        Returns:
            ProviderStartResult:
                success=True  with ``redirect_url`` and ``provider_payment_id``
                              when AcquireMock creates the session successfully.
                success=False with a ``failure_reason`` on any error.
        """
        base_url = settings.ACQUIREMOCK_BASE_URL
        api_key = settings.ACQUIREMOCK_API_KEY
        timeout = getattr(settings, "ACQUIREMOCK_TIMEOUT", 10)

        # --- Fail-closed configuration guards ---
        if not base_url:
            reason = "ACQUIREMOCK_BASE_URL is not configured — cannot initiate payment session."
            logger.error("AcquireMock start failed — %s", reason)
            return ProviderStartResult(success=False, failure_reason=reason)

        if not api_key:
            reason = "ACQUIREMOCK_API_KEY is not configured — cannot authenticate with AcquireMock."
            logger.error("AcquireMock start failed — %s", reason)
            return ProviderStartResult(success=False, failure_reason=reason)

        # --- Financial snapshot validation ---
        if context.payment.amount is None or context.payment.currency is None:
            reason = (
                "Payment amount or currency is missing from the payment snapshot. "
                "Cannot create an AcquireMock session without a financial amount."
            )
            logger.error(
                "AcquireMock start failed — missing amount/currency for order %s",
                context.order.id,
            )
            return ProviderStartResult(success=False, failure_reason=reason)

        url = f"{base_url}{_CREATE_INVOICE_PATH}"
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }
        body = {
            "order_id": str(context.order.id),
            "amount": str(context.payment.amount),
            "currency": str(context.payment.currency),
            "return_url": context.extra.get("return_url", ""),
        }

        try:
            response = requests.post(url, json=body, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            reason = f"AcquireMock network error: {exc}"
            logger.warning("AcquireMock start failed — network error: %s", exc)
            return ProviderStartResult(success=False, failure_reason=reason)

        if not response.ok:
            reason = f"AcquireMock returned HTTP {response.status_code}"
            logger.warning(
                "AcquireMock start failed — HTTP %s for order %s",
                response.status_code,
                context.order.id,
            )
            return ProviderStartResult(success=False, failure_reason=reason)

        try:
            data = response.json()
            payment_id = data["id"]
            redirect_url = data["redirect_url"]
        except (KeyError, ValueError) as exc:
            reason = f"AcquireMock response missing required fields: {exc}"
            logger.warning(
                "AcquireMock start failed — malformed response for order %s: %s",
                context.order.id,
                exc,
            )
            return ProviderStartResult(success=False, failure_reason=reason)

        logger.info(
            "AcquireMock session created for order %s — provider_payment_id=%s",
            context.order.id,
            payment_id,
        )
        return ProviderStartResult(
            success=True,
            provider_payment_id=str(payment_id),
            redirect_url=str(redirect_url),
        )
