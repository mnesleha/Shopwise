from django.db import transaction
from django.utils import timezone

from api.exceptions.base import ConflictException
from carts.models import Cart, CartItem
from carts.services.resolver import hash_cart_token


class CartMergeStockConflict(ConflictException):
    default_detail = "Insufficient stock to merge carts."
    default_code = "CART_MERGE_STOCK_CONFLICT"


def merge_or_adopt_guest_cart(*, user, raw_token: str) -> None:
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
