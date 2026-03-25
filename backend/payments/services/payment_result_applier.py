"""Centralized payment result applier.

Responsible for translating a ProviderStartResult into concrete domain-level
mutations: payment status/timestamps and order status/inventory side-effects.

This module is the single authority for "what does a provider result mean
at the domain level."  Providers never touch order state directly.

Provider result semantics
-------------------------
* success=True, redirect_url=None  — direct/synchronous payment completed
  (e.g. COD via DevFake).  Transition payment → SUCCESS, order → PAID,
  commit inventory.

* success=True, redirect_url set   — hosted/redirect session created
  (e.g. AcquireMock).  The customer has NOT yet paid.  Persist the provider
  reference and redirect URL, leave payment PENDING, leave order CREATED,
  leave inventory ACTIVE.  Final SUCCESS/PAID arrives via webhook.

* success=False                    — provider-side failure.  Transition
  payment → FAILED, order → PAYMENT_FAILED.
"""

from django.utils import timezone

from orders.models import Order
from orders.services.inventory_reservation_service import commit_reservations_for_paid
from payments.models import Payment
from payments.providers.base import ProviderStartResult


def apply_provider_result(
    *,
    payment: Payment,
    order: Order,
    provider_result: ProviderStartResult,
) -> None:
    """Apply a normalized provider result to the payment and order.

    Mutates ``payment`` and ``order`` in place AND persists the changes.
    The caller is responsible for wrapping this in an atomic transaction.

    Args:
        payment:         The Payment record currently in PENDING state.
        order:           The Order being paid (already locked by caller).
        provider_result: Normalized result returned by the provider's start().
    """
    if provider_result.success:
        if provider_result.redirect_url:
            # ----------------------------------------------------------------
            # Hosted/redirect session initiated.  The customer has NOT paid
            # yet — they will be redirected to the hosted payment page.
            # Final SUCCESS/PAID arrives exclusively via the provider webhook.
            # Keep payment PENDING and order in its current non-final state.
            # ----------------------------------------------------------------
            pending_fields: list[str] = []

            if provider_result.provider_payment_id:
                payment.provider_payment_id = provider_result.provider_payment_id
                pending_fields.append("provider_payment_id")

            payment.redirect_url = provider_result.redirect_url
            pending_fields.append("redirect_url")

            if pending_fields:
                payment.save(update_fields=pending_fields)

            # payment.status remains PENDING; order.status remains CREATED;
            # inventory reservations remain ACTIVE.
        else:
            # ----------------------------------------------------------------
            # Direct/synchronous payment completed (e.g. COD/DevFake).
            # Finalize immediately.
            # ----------------------------------------------------------------
            payment.status = Payment.Status.SUCCESS
            payment.paid_at = timezone.now()
            success_fields = ["status", "paid_at"]

            if provider_result.provider_payment_id:
                payment.provider_payment_id = provider_result.provider_payment_id
                success_fields.append("provider_payment_id")

            payment.save(update_fields=success_fields)

            # commit_reservations_for_paid decrements stock, commits reservations,
            # and sets order.status = PAID (in-memory and persisted) when the order
            # has active reservations.  For orders without reservations (rare but
            # valid — e.g. all-digital goods), it returns early without touching
            # the order status, so we handle that case with an explicit fallback save.
            commit_reservations_for_paid(order=order)
            if order.status != Order.Status.PAID:
                order.status = Order.Status.PAID
                order.save(update_fields=["status"])
    else:
        payment.status = Payment.Status.FAILED
        payment.failed_at = timezone.now()
        payment.failure_reason = provider_result.failure_reason
        payment.save(update_fields=["status", "failed_at", "failure_reason"])

        order.status = Order.Status.PAYMENT_FAILED
        order.cancel_reason = Order.CancelReason.PAYMENT_FAILED
        order.save(update_fields=["status", "cancel_reason"])
