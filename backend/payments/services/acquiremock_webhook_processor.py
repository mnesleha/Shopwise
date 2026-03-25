"""AcquireMock webhook event processor (Slice PR2/3).

Translates a verified, normalised AcquireMockWebhookEvent into concrete
payment and order domain mutations by delegating to the central
apply_provider_result() authority.

Responsibilities:
- Resolve the Payment record from the AcquireMock-side payment_id.
- Guard against re-processing already-terminal payments (idempotence).
- Map AcquireMock status strings to ProviderStartResult values.
- Delegate all domain mutations to apply_provider_result().
- Wrap the entire operation in a DB transaction with a row-level lock.
"""

import logging

from django.db import transaction

from payments.models import Payment
from payments.providers.acquiremock_webhook import AcquireMockWebhookEvent
from payments.providers.base import ProviderStartResult
from payments.services.payment_result_applier import apply_provider_result

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AcquireMockPaymentNotFound(Exception):
    """Raised when no ACQUIREMOCK Payment matches the webhook's payment_id."""


# ---------------------------------------------------------------------------
# Internal status map
# ---------------------------------------------------------------------------

_STATUS_MAP: dict[str, ProviderStartResult] = {
    "PAID": ProviderStartResult(success=True),
    "FAILED": ProviderStartResult(success=False, failure_reason="Payment failed by provider"),
    "EXPIRED": ProviderStartResult(success=False, failure_reason="Payment expired"),
}

# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------


def process_acquiremock_webhook_event(event: AcquireMockWebhookEvent) -> None:
    """Process a verified AcquireMock webhook event.

    Looks up the Payment record, checks for already-terminal state (idempotence),
    maps the provider status, and delegates to apply_provider_result().

    Args:
        event: Normalised, signature-verified AcquireMockWebhookEvent.

    Raises:
        AcquireMockPaymentNotFound: No ACQUIREMOCK Payment with the given
            provider_payment_id exists.
        ValueError: The event's status string is not in the supported set
            (PAID, FAILED, EXPIRED).
    """
    # Validate status before touching the DB so we fail fast on bad input.
    if event.status not in _STATUS_MAP:
        raise ValueError(
            f"Unsupported AcquireMock status: {event.status!r}. "
            f"Supported: {sorted(_STATUS_MAP)}"
        )

    with transaction.atomic():
        # Lock the Payment row to prevent concurrent webhook deliveries from
        # racing against each other or the checkout flow.
        try:
            payment = (
                Payment.objects.select_for_update()
                .select_related("order")
                .filter(
                    provider_payment_id=event.payment_id,
                    provider=Payment.Provider.ACQUIREMOCK,
                )
                .get()
            )
        except Payment.DoesNotExist:
            raise AcquireMockPaymentNotFound(
                f"No ACQUIREMOCK payment found with provider_payment_id={event.payment_id!r}"
            )

        # Idempotence guard — if the payment is already in a terminal state we
        # have nothing to do.  Return silently so the caller can respond 200 OK
        # and AcquireMock does not re-deliver the same event indefinitely.
        if payment.status in (Payment.Status.SUCCESS, Payment.Status.FAILED):
            logger.info(
                "AcquireMock webhook skipped — payment already terminal "
                "(provider_payment_id=%s, current_status=%s)",
                event.payment_id,
                payment.status,
            )
            return

        provider_result = _STATUS_MAP[event.status]

        logger.info(
            "Applying AcquireMock webhook: provider_payment_id=%s status=%s success=%s",
            event.payment_id,
            event.status,
            provider_result.success,
        )

        apply_provider_result(
            payment=payment,
            order=payment.order,
            provider_result=provider_result,
        )
