from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from carts.models import ActiveCart, Cart


def _bind_pointer_to_cart(user, cart: Cart, ptr: ActiveCart | None) -> tuple[Cart, bool]:
    """Bind the user's pointer row to the resolved active cart, recovering from races."""
    if ptr:
        ptr.cart = cart
        ptr.save(update_fields=["cart", "updated_at"])
        return cart, False

    try:
        with transaction.atomic():
            ActiveCart.objects.create(user=user, cart=cart)
        return cart, False
    except IntegrityError:
        current_ptr = (
            ActiveCart.objects.select_for_update()
            .filter(user=user)
            .select_related("cart")
            .first()
        )
        if current_ptr and current_ptr.cart.status == Cart.Status.ACTIVE:
            return current_ptr.cart, False
        if current_ptr:
            current_ptr.cart = cart
            current_ptr.save(update_fields=["cart", "updated_at"])
        return cart, False


@transaction.atomic
def get_or_create_active_cart_for_user(user) -> tuple[Cart, bool]:
    """
    Concurrency-safe resolver for authenticated users.

    Ensures exactly one 'current' ACTIVE cart per user using an ActiveCart
    pointer row guarded by SELECT ... FOR UPDATE.
    """
    user_model = get_user_model()
    user = user_model.objects.select_for_update().get(pk=user.pk)

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
        return _bind_pointer_to_cart(user, existing, ptr)

    # Create a fresh ACTIVE cart (old one might be CONVERTED / MERGED).
    try:
        with transaction.atomic():
            cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    except (ValidationError, IntegrityError):
        existing = (
            Cart.objects.filter(user=user, status=Cart.Status.ACTIVE)
            .order_by("-created_at", "-id")
            .first()
        )
        if existing:
            return _bind_pointer_to_cart(user, existing, ptr)
        raise

    if ptr:
        ptr.cart = cart
        ptr.save(update_fields=["cart", "updated_at"])
        return cart, True

    try:
        with transaction.atomic():
            ActiveCart.objects.create(user=user, cart=cart)
        return cart, True
    except IntegrityError:
        existing = (
            Cart.objects.filter(user=user, status=Cart.Status.ACTIVE)
            .order_by("-created_at", "-id")
            .first()
        )
        if existing:
            return _bind_pointer_to_cart(user, existing, None)
        raise
