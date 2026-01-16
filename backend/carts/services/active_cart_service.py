from __future__ import annotations

from django.db import transaction

from carts.models import ActiveCart, Cart


@transaction.atomic
def get_or_create_active_cart_for_user(user) -> tuple[Cart, bool]:
    """
    Concurrency-safe resolver for authenticated users.

    Ensures exactly one 'current' ACTIVE cart per user using an ActiveCart
    pointer row guarded by SELECT ... FOR UPDATE.
    """
    ptr = (
        ActiveCart.objects.select_for_update()
        .filter(user=user)
        .select_related("cart")
        .first()
    )

    if ptr and ptr.cart.status == Cart.Status.ACTIVE:
        return ptr.cart, False

    # If pointer is missing/stale but user already has an ACTIVE cart, adopt it
    existing = (
        Cart.objects.filter(user=user, status=Cart.Status.ACTIVE)
        .order_by("-created_at", "-id")
        .first()
    )
    if existing:
        if ptr:
            ptr.cart = existing
            ptr.save(update_fields=["cart", "updated_at"])
        else:
            ActiveCart.objects.create(user=user, cart=existing)
        return existing, False

    # Create a fresh ACTIVE cart (old one might be CONVERTED / MERGED).
    cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)

    if ptr:
        ptr.cart = cart
        ptr.save(update_fields=["cart", "updated_at"])
    else:
        ActiveCart.objects.create(user=user, cart=cart)

    return cart, True
