from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from categories.models import Category
from discounts.models import Offer, OrderPromotion, Promotion, PromotionCategory, PromotionProduct
from products.models import Product

from utils.seed.demo.config import DEMO_LINE_PROMOTIONS, DEMO_OFFERS, DEMO_ORDER_PROMOTIONS


WriteLine = Callable[[str], None]


def seed_demo_commercial_layer(write: WriteLine) -> dict[str, dict[str, Any]]:
    line_promotions = _seed_line_promotions(write)
    order_promotions, promotions_by_code = _seed_order_promotions(write)
    offers = _seed_offers(write, promotions_by_code=promotions_by_code)
    return {
        "line_promotions": line_promotions,
        "order_promotions": order_promotions,
        "offers": offers,
    }


def _seed_line_promotions(write: WriteLine) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}
    category_map = {category.name: category for category in Category.objects.all()}
    product_map = {product.slug: product for product in Product.objects.exclude(slug__isnull=True)}

    for promotion_data in DEMO_LINE_PROMOTIONS:
        promotion, created = Promotion.objects.update_or_create(
            code=promotion_data["code"],
            defaults={
                "name": promotion_data["name"],
                "type": promotion_data["type"],
                "value": Decimal(promotion_data["value"]),
                "amount_scope": promotion_data["amount_scope"],
                "priority": promotion_data["priority"],
                "description": promotion_data["description"],
                "is_active": True,
                "active_from": None,
                "active_to": None,
            },
        )

        kept_product_target_ids: list[int] = []
        for slug in promotion_data["product_slugs"]:
            target, _ = PromotionProduct.objects.update_or_create(
                promotion=promotion,
                product=product_map[slug],
            )
            kept_product_target_ids.append(target.id)
        _delete_unkept_targets(
            PromotionProduct.objects.filter(promotion=promotion),
            kept_product_target_ids,
        )

        kept_category_target_ids: list[int] = []
        for name in promotion_data["category_names"]:
            target, _ = PromotionCategory.objects.update_or_create(
                promotion=promotion,
                category=category_map[name],
            )
            kept_category_target_ids.append(target.id)
        _delete_unkept_targets(
            PromotionCategory.objects.filter(promotion=promotion),
            kept_category_target_ids,
        )

        fixtures[promotion_data["key"]] = {
            "id": promotion.id,
            "code": promotion.code,
            "product_targets": len(kept_product_target_ids),
            "category_targets": len(kept_category_target_ids),
        }
        write(f"{'Created' if created else 'Updated'} line promotion: {promotion.name}")

    return fixtures


def _seed_order_promotions(
    write: WriteLine,
) -> tuple[dict[str, dict[str, Any]], dict[str, OrderPromotion]]:
    fixtures: dict[str, dict[str, Any]] = {}
    promotions_by_code: dict[str, OrderPromotion] = {}

    for promotion_data in DEMO_ORDER_PROMOTIONS:
        minimum_order_value = promotion_data.get("minimum_order_value")
        promotion, created = OrderPromotion.objects.update_or_create(
            code=promotion_data["code"],
            defaults={
                "name": promotion_data["name"],
                "type": promotion_data["type"],
                "value": Decimal(promotion_data["value"]),
                "acquisition_mode": promotion_data["acquisition_mode"],
                "stacking_policy": promotion_data["stacking_policy"],
                "priority": promotion_data["priority"],
                "minimum_order_value": (
                    Decimal(minimum_order_value)
                    if minimum_order_value is not None
                    else None
                ),
                "is_discoverable": promotion_data["is_discoverable"],
                "description": promotion_data["description"],
                "is_active": True,
                "active_from": None,
                "active_to": None,
            },
        )
        promotions_by_code[promotion.code] = promotion
        fixtures[promotion_data["key"]] = {
            "id": promotion.id,
            "code": promotion.code,
            "acquisition_mode": promotion.acquisition_mode,
        }
        write(f"{'Created' if created else 'Updated'} order promotion: {promotion.name}")

    return fixtures, promotions_by_code


def _seed_offers(
    write: WriteLine,
    *,
    promotions_by_code: dict[str, OrderPromotion],
) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}
    kept_offer_ids_by_promotion: dict[int, list[int]] = defaultdict(list)

    for offer_data in DEMO_OFFERS:
        promotion = promotions_by_code[offer_data["promotion_code"]]
        offer, created = Offer.objects.update_or_create(
            token=offer_data["token"],
            defaults={
                "promotion": promotion,
                "status": offer_data["status"],
                "is_active": offer_data["is_active"],
                "active_from": None,
                "active_to": None,
                "description": offer_data["description"],
            },
        )
        kept_offer_ids_by_promotion[promotion.id].append(offer.id)
        fixtures[offer_data["key"]] = {
            "id": offer.id,
            "token": offer.token,
            "promotion_code": promotion.code,
        }
        write(f"{'Created' if created else 'Updated'} offer token: {offer.token}")

    for promotion in promotions_by_code.values():
        _delete_unkept_targets(
            Offer.objects.filter(promotion=promotion),
            kept_offer_ids_by_promotion.get(promotion.id, []),
        )

    return fixtures


def _delete_unkept_targets(queryset, kept_ids: list[int]) -> None:
    if kept_ids:
        queryset.exclude(id__in=kept_ids).delete()
    else:
        queryset.delete()