from django.db import transaction
from django.utils import timezone
from typing import Optional, TypedDict
from api.exceptions.base import ConflictException
from carts.models import Cart, CartItem
from carts.services.resolver import hash_cart_token


class CartMergeStockConflict(ConflictException):
    """
    Kept for backward compatibility with existing imports/tests.
    merge_or_adopt_guest_cart no longer raises this — it caps quantities
    and records a STOCK_ADJUSTED warning in the report instead.
    """

    default_detail = "Insufficient stock to merge carts."
    default_code = "CART_MERGE_STOCK_CONFLICT"


class CartMergeWarning(TypedDict):
    code: str          # e.g. "STOCK_ADJUSTED"
    product_id: int
    requested: int
    applied: int


class CartMergeReport(TypedDict):
    performed: bool
    result: str        # "NOOP" | "ADOPTED" | "MERGED"
    items_added: int
    items_updated: int
    items_removed: int
    warnings: list     # list[CartMergeWarning]


def _noop_report() -> CartMergeReport:
    return CartMergeReport(
        performed=False,
        result="NOOP",
        items_added=0,
        items_updated=0,
        items_removed=0,
        warnings=[],
    )


def merge_or_adopt_guest_cart(*, user, raw_token: Optional[str]) -> CartMergeReport:
    """
    Merge or adopt an anonymous (guest) cart into the authenticated user's cart.

    Idempotent: repeated calls with the same token are a no-op after the first
    successful call (the anonymous cart is MERGED/ADOPTED and its token cleared).

    Stock handling:
        Instead of raising CartMergeStockConflict, quantities that would exceed
        available stock are *capped* to the available amount and a STOCK_ADJUSTED
        warning is added to the report.  Items that have zero available stock are
        skipped entirely (not moved to the user cart).

    Returns:
        CartMergeReport dict describing what was done.
    """

    if not raw_token:
        return _noop_report()

    token_hash = hash_cart_token(raw_token)

    with transaction.atomic():
        try:
            anonymous_cart = Cart.objects.select_for_update().get(
                user__isnull=True,
                status=Cart.Status.ACTIVE,
                anonymous_token_hash=token_hash,
            )
        except Cart.DoesNotExist:
            return _noop_report()

        user_cart = Cart.objects.select_for_update().filter(
            user=user,
            status=Cart.Status.ACTIVE,
        ).first()

        warnings: list = []

        # ------------------------------------------------------------------ ADOPT
        # No active user cart exists — adopt the guest cart directly.
        if user_cart is None:
            items_added = 0
            anon_items = list(CartItem.objects.filter(cart=anonymous_cart).select_related("product"))

            for item in anon_items:
                available = item.product.stock_quantity
                applied = min(item.quantity, available)
                if applied <= 0:
                    # No stock at all — drop the item entirely.
                    warnings.append(CartMergeWarning(
                        code="STOCK_ADJUSTED",
                        product_id=item.product.id,
                        requested=item.quantity,
                        applied=0,
                    ))
                    item.delete()
                    continue
                if applied < item.quantity:
                    warnings.append(CartMergeWarning(
                        code="STOCK_ADJUSTED",
                        product_id=item.product.id,
                        requested=item.quantity,
                        applied=applied,
                    ))
                    item.quantity = applied
                    item.save(update_fields=["quantity"])
                items_added += 1

            anonymous_cart.user = user
            anonymous_cart.anonymous_token_hash = None
            anonymous_cart.merged_into_cart = None
            anonymous_cart.merged_at = None
            anonymous_cart.save(
                update_fields=[
                    "user",
                    "anonymous_token_hash",
                    "merged_into_cart",
                    "merged_at",
                ]
            )
            return CartMergeReport(
                performed=True,
                result="ADOPTED",
                items_added=items_added,
                items_updated=0,
                items_removed=0,
                warnings=warnings,
            )

        # ------------------------------------------------------------------ MERGE
        # User already has an active cart — merge guest items into it.
        user_items = {
            item.product_id: item
            for item in CartItem.objects.select_for_update()
            .select_related("product")
            .filter(cart=user_cart)
        }
        anonymous_items = list(
            CartItem.objects.select_for_update()
            .select_related("product")
            .filter(cart=anonymous_cart)
        )

        items_to_update = []
        items_to_move = []
        anonymous_ids_to_delete = []
        items_updated = 0
        items_added = 0

        for anonymous_item in anonymous_items:
            product = anonymous_item.product
            user_item = user_items.get(anonymous_item.product_id)

            if user_item:
                # Product already in user cart — sum quantities, cap to stock.
                merged_quantity = user_item.quantity + anonymous_item.quantity
                available = product.stock_quantity
                applied = min(merged_quantity, available)
                if applied < merged_quantity:
                    warnings.append(CartMergeWarning(
                        code="STOCK_ADJUSTED",
                        product_id=product.id,
                        requested=merged_quantity,
                        applied=applied,
                    ))
                user_item.quantity = applied
                items_to_update.append(user_item)
                anonymous_ids_to_delete.append(anonymous_item.id)
                items_updated += 1
            else:
                # New product — move guest item to user cart, capping to stock.
                available = product.stock_quantity
                applied = min(anonymous_item.quantity, available)
                if applied <= 0:
                    # Drop the item — no stock available.
                    warnings.append(CartMergeWarning(
                        code="STOCK_ADJUSTED",
                        product_id=product.id,
                        requested=anonymous_item.quantity,
                        applied=0,
                    ))
                    anonymous_ids_to_delete.append(anonymous_item.id)
                    continue
                if applied < anonymous_item.quantity:
                    warnings.append(CartMergeWarning(
                        code="STOCK_ADJUSTED",
                        product_id=product.id,
                        requested=anonymous_item.quantity,
                        applied=applied,
                    ))
                    anonymous_item.quantity = applied
                anonymous_item.cart = user_cart
                items_to_move.append(anonymous_item)
                items_added += 1

        if items_to_update:
            CartItem.objects.bulk_update(items_to_update, ["quantity"])
        if items_to_move:
            CartItem.objects.bulk_update(items_to_move, ["cart", "quantity"])
        if anonymous_ids_to_delete:
            CartItem.objects.filter(id__in=anonymous_ids_to_delete).delete()

        anonymous_cart.status = Cart.Status.MERGED
        anonymous_cart.anonymous_token_hash = None
        anonymous_cart.merged_into_cart = user_cart
        anonymous_cart.merged_at = timezone.now()
        anonymous_cart.save(
            update_fields=[
                "status",
                "anonymous_token_hash",
                "merged_into_cart",
                "merged_at",
            ]
        )
        return CartMergeReport(
            performed=True,
            result="MERGED",
            items_added=items_added,
            items_updated=items_updated,
            items_removed=0,
            warnings=warnings,
        )

    """
    Merge or adopt an anonymous (guest) cart into the authenticated user's cart.

    This function is idempotent: repeated calls with the same token will not duplicate merges.

    Args:
        user: Authenticated user instance.
        raw_token: Guest cart token from request header/cookie. Can be None/empty.

    Raises:
        CartMergeStockConflict: If merging quantities would exceed available product stock.
    """

    if not raw_token:
        return

    token_hash = hash_cart_token(raw_token)

    with transaction.atomic():
        try:
            anonymous_cart = Cart.objects.select_for_update().get(
                user__isnull=True,
                status=Cart.Status.ACTIVE,
                anonymous_token_hash=token_hash,
            )
        except Cart.DoesNotExist:
            return

        user_cart = Cart.objects.select_for_update().filter(
            user=user,
            status=Cart.Status.ACTIVE,
        ).first()

        if user_cart is None:
            anonymous_cart.user = user
            anonymous_cart.anonymous_token_hash = None
            anonymous_cart.merged_into_cart = None
            anonymous_cart.merged_at = None
            anonymous_cart.save(
                update_fields=[
                    "user",
                    "anonymous_token_hash",
                    "merged_into_cart",
                    "merged_at",
                ]
            )
            return

        user_items = {
            item.product_id: item
            for item in CartItem.objects.select_for_update()
            .select_related("product")
            .filter(cart=user_cart)
        }
        anonymous_items = list(
            CartItem.objects.select_for_update()
            .select_related("product")
            .filter(cart=anonymous_cart)
        )

        items_to_update = []
        items_to_move = []
        anonymous_ids_to_delete = []

        for anonymous_item in anonymous_items:
            product = anonymous_item.product
            user_item = user_items.get(anonymous_item.product_id)

            if user_item:
                merged_quantity = user_item.quantity + anonymous_item.quantity
                if merged_quantity > product.stock_quantity:
                    raise CartMergeStockConflict(
                        detail=f"Insufficient stock to merge product {product.id}."
                    )
                user_item.quantity = merged_quantity
                items_to_update.append(user_item)
                anonymous_ids_to_delete.append(anonymous_item.id)
            else:
                if anonymous_item.quantity > product.stock_quantity:
                    raise CartMergeStockConflict(
                        detail=f"Insufficient stock to merge product {product.id}."
                    )
                anonymous_item.cart = user_cart
                items_to_move.append(anonymous_item)

        if items_to_update:
            CartItem.objects.bulk_update(items_to_update, ["quantity"])
        if items_to_move:
            CartItem.objects.bulk_update(items_to_move, ["cart"])
        if anonymous_ids_to_delete:
            CartItem.objects.filter(id__in=anonymous_ids_to_delete).delete()

        anonymous_cart.status = Cart.Status.MERGED
        anonymous_cart.anonymous_token_hash = None
        anonymous_cart.merged_into_cart = user_cart
        anonymous_cart.merged_at = timezone.now()
        anonymous_cart.save(
            update_fields=[
                "status",
                "anonymous_token_hash",
                "merged_into_cart",
                "merged_at",
            ]
        )
