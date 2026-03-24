"""Centralized payment result applier.

Responsible for translating a ProviderStartResult into concrete domain-level
mutations: payment status/timestamps and order status/inventory side-effects.

This module is the single authority for "what does a provider result mean
at the domain level."  Providers never touch order state directly.
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
        payment.status = Payment.Status.SUCCESS
        payment.paid_at = timezone.now()
        payment.save(update_fields=["status", "paid_at"])

        commit_reservations_for_paid(order=order)
        order.refresh_from_db()
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
