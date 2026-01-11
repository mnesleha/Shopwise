from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from orders.models import Order


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def claim_guest_orders_for_user(user) -> int:
    if not getattr(user, "email_verified", False):
        return 0

    normalized_email = _normalize_email(user.email)

    with transaction.atomic():
        candidates = (
            Order.objects.select_for_update()
            .filter(user__isnull=True, is_claimed=False)
            .filter(
                Q(customer_email_normalized=normalized_email)
            )
        )
        now = timezone.now()
        to_update = []

        for order in candidates:
            order_email = order.customer_email_normalized
            if not order_email and order.customer_email:
                order_email = _normalize_email(order.customer_email)

            if order_email != normalized_email:
                continue

            order.user = user
            order.is_claimed = True
            order.claimed_at = now
            order.claimed_by_user = user
            order.customer_email_normalized = order_email
            to_update.append(order)

        if to_update:
            Order.objects.bulk_update(
                to_update,
                [
                    "user",
                    "is_claimed",
                    "claimed_at",
                    "claimed_by_user",
                    "customer_email_normalized",
                ],
            )

        return len(to_update)
