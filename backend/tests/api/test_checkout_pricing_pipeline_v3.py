"""Checkout pricing authority switch — Phase 3 regression tests.

Verifies that:
- Checkout uses the current pricing pipeline (get_cart_pricing) as the
  authoritative source, not the legacy calculate_price / Discount model.
- Promoted and non-promoted cart items are priced consistently at checkout.
- price_at_add_time is retained on CartItem but is not the checkout authority:
  the order item snapshot reflects the live pipeline output, which may differ
  from price_at_add_time.
- Checkout happy path produces a valid Order with correct totals.
- PERCENT and FIXED promotions are correctly propagated to order item snapshots.
- Category-targeted promotions are honoured at checkout.
- A cart with mixed promoted / non-promoted items produces individual correct
  line totals and an accurate aggregate total.
"""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from categories.models import Category
from carts.models import CartItem
from discounts.models import (
    Promotion,
    PromotionAmountScope,
    PromotionCategory,
    PromotionProduct,
    PromotionType,
)
from products.models import Product, TaxClass
from tests.conftest import checkout_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tax_class(code: str, rate: Decimal) -> TaxClass:
    return TaxClass.objects.create(name=code.title(), code=code, rate=rate)


def _category(name: str = "Electronics") -> Category:
    return Category.objects.create(name=name)


def _product(
    *,
    name: str,
    price_net: Decimal,
    tax_class: TaxClass | None = None,
    category: Category | None = None,
    stock: int = 10,
) -> Product:
    """Create a migrated product (price_net_amount set)."""
    return Product.objects.create(
        name=name,
        price=price_net,
        stock_quantity=stock,
        is_active=True,
        price_net_amount=price_net,
        currency="EUR",
        tax_class=tax_class,
        category=category,
    )


def _promo_on_product(
    product: Product,
    *,
    code: str,
    promo_type: str = PromotionType.PERCENT,
    value: Decimal,
    priority: int = 5,
    amount_scope: str = PromotionAmountScope.GROSS,
) -> Promotion:
    promo = Promotion.objects.create(
        name=f"Promo {code}",
        code=code,
        type=promo_type,
        value=value,
        priority=priority,
        is_active=True,
        amount_scope=amount_scope,
    )
    PromotionProduct.objects.create(promotion=promo, product=product)
    return promo


def _promo_on_category(
    category: Category,
    *,
    code: str,
    promo_type: str = PromotionType.PERCENT,
    value: Decimal,
    priority: int = 5,
) -> Promotion:
    promo = Promotion.objects.create(
        name=f"Promo {code}",
        code=code,
        type=promo_type,
        value=value,
        priority=priority,
        is_active=True,
    )
    PromotionCategory.objects.create(promotion=promo, category=category)
    return promo


def _do_checkout(client, product: Product, quantity: int = 1):
    """Add product to cart and execute checkout.  Returns (response, data)."""
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": quantity},
        format="json",
    )
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    return response, response.json()


# ---------------------------------------------------------------------------
# Checkout happy path — no promotion
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_checkout_happy_path_no_promotion(auth_client):
    """Checkout with a single non-promoted migrated product succeeds."""
    product = _product(name="Basic Widget", price_net=Decimal("49.99"))

    response, data = _do_checkout(auth_client, product)

    assert response.status_code == 201
    assert data["total"] == "49.99"
    item = data["items"][0]
    assert item["unit_price"] == "49.99"
    assert item["line_total"] == "49.99"
    assert item["discount"] is None


# ---------------------------------------------------------------------------
# PERCENT promotion reflected correctly in order item snapshot
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_percent_promotion_reflected_in_order_item_snapshot(auth_client):
    """A PERCENT promotion reduces the unit_price and creates a discount snapshot."""
    product = _product(name="Discounted Widget", price_net=Decimal("100.00"))
    _promo_on_product(
        product,
        code="save-10pct",
        promo_type=PromotionType.PERCENT,
        value=Decimal("10.00"),
    )

    response, data = _do_checkout(auth_client, product)

    assert response.status_code == 201
    assert data["total"] == "90.00"
    item = data["items"][0]
    assert item["unit_price"] == "90.00"
    assert item["line_total"] == "90.00"
    assert item["discount"] is not None
    assert item["discount"]["type"] == "PERCENT"
    # applied_discount_value_at_order_time holds the computed percentage.
    assert item["discount"]["value"] == "10.00"


# ---------------------------------------------------------------------------
# FIXED GROSS promotion reflected correctly in order item snapshot
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_fixed_gross_promotion_reflected_in_order_item_snapshot(auth_client):
    """A FIXED GROSS promotion reduces the gross unit price and creates a discount snapshot."""
    product = _product(name="Sale Widget", price_net=Decimal("80.00"))
    _promo_on_product(
        product,
        code="minus-15-eur",
        promo_type=PromotionType.FIXED,
        value=Decimal("15.00"),
        amount_scope=PromotionAmountScope.GROSS,
    )

    response, data = _do_checkout(auth_client, product)

    assert response.status_code == 201
    assert data["total"] == "65.00"
    item = data["items"][0]
    assert item["unit_price"] == "65.00"
    assert item["discount"]["type"] == "FIXED"
    assert item["discount"]["value"] == "15.00"


# ---------------------------------------------------------------------------
# Category-targeted promotion is honoured at checkout
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_category_promotion_applied_at_checkout(auth_client):
    """A promotion targeting a product's category is applied at checkout."""
    cat = _category(name="Gadgets")
    product = _product(name="Gadget", price_net=Decimal("200.00"), category=cat)
    _promo_on_category(cat, code="gadget-20pct", value=Decimal("20.00"))

    response, data = _do_checkout(auth_client, product)

    assert response.status_code == 201
    assert data["total"] == "160.00"


# ---------------------------------------------------------------------------
# Multi-item cart: promoted + non-promoted items
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mixed_cart_promoted_and_non_promoted(auth_client):
    """Each item in a mixed cart is priced independently; aggregate total is correct."""
    product_a = _product(name="Widget A", price_net=Decimal("100.00"))
    product_b = _product(name="Widget B", price_net=Decimal("50.00"))
    _promo_on_product(
        product_a,
        code="widget-a-10pct",
        promo_type=PromotionType.PERCENT,
        value=Decimal("10.00"),
    )
    # product_b has no promotion

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product_a.id, "quantity": 1},
        format="json",
    )
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product_b.id, "quantity": 2},
        format="json",
    )

    response = auth_client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    data = response.json()

    assert response.status_code == 201
    # product_a: 100 − 10 % = 90; product_b: 50 × 2 = 100; total = 190
    assert data["total"] == "190.00"

    by_product = {str(item["product"]): item for item in data["items"]}
    item_a = by_product[str(product_a.id)]
    item_b = by_product[str(product_b.id)]

    assert item_a["unit_price"] == "90.00"
    assert item_a["discount"] is not None

    assert item_b["unit_price"] == "50.00"
    assert item_b["discount"] is None


# ---------------------------------------------------------------------------
# price_at_add_time is retained but is not the order item authority
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_price_at_add_time_retained_but_non_authoritative(auth_client):
    """price_at_add_time is preserved on CartItem, but order item reflects live pricing.

    After Phase 3 the authoritative checkout price is the current pricing pipeline.
    price_at_add_time may differ from the order item unit_price when the price changed
    between add-to-cart and checkout.  This test verifies that:
    1. CartItem.price_at_add_time is set correctly at add time.
    2. The order item unit_price_at_order_time reflects the live price, not the snapshot.
    """
    from carts.models import Cart

    product = _product(name="Snapshot Test", price_net=Decimal("100.00"))

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    # Verify the snapshot was captured correctly at add time.
    cart = Cart.objects.filter(status=Cart.Status.ACTIVE).last()
    cart_item = cart.items.get(product=product)
    assert cart_item.price_at_add_time == Decimal("100.00")

    # Merchant raises price before checkout.
    product.price = Decimal("150.00")
    product.price_net_amount = Decimal("150.00")
    product.save()

    response = auth_client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    data = response.json()

    assert response.status_code == 201
    item = data["items"][0]
    # Order item reflects LIVE price (150.00), not the snapshot (100.00).
    assert item["unit_price"] == "150.00"
    assert data["total"] == "150.00"


# ---------------------------------------------------------------------------
# Tax-inclusive pricing passes through correctly
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_checkout_with_tax_class_applies_correct_gross(auth_client):
    """For products with a tax class the checkout total reflects the taxed gross."""
    tc = _tax_class("vat23", rate=Decimal("23"))
    # net €100 at 23 % → gross €123
    product = _product(name="Taxed Widget", price_net=Decimal("100.00"), tax_class=tc)

    response, data = _do_checkout(auth_client, product)

    assert response.status_code == 201
    assert data["total"] == "123.00"
    item = data["items"][0]
    assert item["unit_price"] == "123.00"
    assert item["discount"] is None


# ---------------------------------------------------------------------------
# PERCENT promotion applied on top of tax — tax calculated on discounted NET
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_promotion_applied_before_tax_at_checkout(auth_client):
    """Tax is calculated on the post-discount NET, consistent with catalogue behaviour."""
    tc = _tax_class("vat10", rate=Decimal("10"))
    # net €100, PERCENT 20 % → discounted net €80 → gross €88 (10 % on 80)
    product = _product(name="Taxed Discounted", price_net=Decimal("100.00"), tax_class=tc)
    _promo_on_product(
        product,
        code="taxed-20pct",
        promo_type=PromotionType.PERCENT,
        value=Decimal("20.00"),
    )

    response, data = _do_checkout(auth_client, product)

    assert response.status_code == 201
    assert data["total"] == "88.00"
