"""API tests for Phase 2 / Slice 4 — cart pricing integration.

Covers:
- empty cart returns safe zero totals
- cart item without promotion: undiscounted == discounted
- product-targeted promotion reduces cart item discounted pricing
- category-targeted promotion reduces cart item discounted pricing
- tax is calculated from discounted NET (not undiscounted NET)
- cart totals aggregate correctly across multiple items
- cart totals structure is complete (all required keys present)
- items structure is complete (pricing sub-key present on every item)
- unmigrated products (no price_net_amount) return safe null item pricing
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from categories.models import Category
from discounts.models import Promotion, PromotionCategory, PromotionProduct, PromotionType
from products.models import Product, TaxClass

User = get_user_model()


CART_URL = "/api/v1/cart/"
CART_ITEMS_URL = "/api/v1/cart/items/"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(suffix: str = "") -> "User":
    return User.objects.create_user(
        email=f"cartprice{suffix}@example.com",
        password="Test1234!",
    )


def _auth_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _tax_class(*, code: str, rate=None) -> TaxClass:
    return TaxClass.objects.create(name=code.title(), code=code, rate=rate)


def _category(name: str) -> Category:
    return Category.objects.create(name=name)


def _product(
    *,
    name: str = "Widget",
    price_net_amount=None,
    currency: str = "EUR",
    tax_class=None,
    category=None,
) -> Product:
    return Product.objects.create(
        name=name,
        price=price_net_amount if price_net_amount is not None else Decimal("9.99"),
        stock_quantity=10,
        is_active=True,
        price_net_amount=price_net_amount,
        currency=currency,
        tax_class=tax_class,
        category=category,
    )


def _promotion(
    *,
    code: str,
    promo_type: str = PromotionType.PERCENT,
    value: Decimal,
    priority: int = 5,
) -> Promotion:
    return Promotion.objects.create(
        name=f"Promo {code}",
        code=code,
        type=promo_type,
        value=value,
        priority=priority,
        is_active=True,
    )


def _add_item(client: APIClient, product: Product, quantity: int = 1) -> None:
    resp = client.post(
        CART_ITEMS_URL,
        {"product_id": product.id, "quantity": quantity},
        format="json",
    )
    assert resp.status_code in (200, 201), resp.json()


# ---------------------------------------------------------------------------
# Empty cart — safe zero totals
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_empty_cart_returns_safe_totals():
    """Empty cart must return all-zero totals without errors."""
    u = _user("empty")
    client = _auth_client(u)

    resp = client.get(CART_URL)
    assert resp.status_code in (200, 201)
    data = resp.json()

    assert data["items"] == []

    totals = data["totals"]
    assert totals["subtotal_undiscounted"] == "0.00"
    assert totals["subtotal_discounted"] == "0.00"
    assert totals["total_discount"] == "0.00"
    assert totals["total_tax"] == "0.00"
    assert totals["total_gross"] == "0.00"
    assert totals["item_count"] == 0


# ---------------------------------------------------------------------------
# Item pricing structure
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cart_item_pricing_structure_complete():
    """Each cart item must expose a pricing sub-key with undiscounted/discounted/discount."""
    u = _user("struct")
    client = _auth_client(u)
    tc = _tax_class(code="struct_std", rate=Decimal("23"))
    p = _product(name="Struct", price_net_amount=Decimal("50.00"), tax_class=tc)

    _add_item(client, p)
    resp = client.get(CART_URL)
    assert resp.status_code == 200

    item = resp.json()["items"][0]
    assert "pricing" in item
    pricing = item["pricing"]
    assert set(pricing.keys()) >= {"undiscounted", "discounted", "discount"}
    for tier in ("undiscounted", "discounted"):
        assert {"net", "gross", "tax", "currency", "tax_rate"} <= set(pricing[tier].keys())
    assert {"amount_net", "amount_gross", "percentage", "promotion_code", "promotion_type"} <= set(
        pricing["discount"].keys()
    )


# ---------------------------------------------------------------------------
# No-promotion baseline
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cart_item_without_promotion_undiscounted_equals_discounted():
    """Cart item with no active promotion: undiscounted tier == discounted tier."""
    u = _user("nopromo")
    client = _auth_client(u)
    tc = _tax_class(code="np_std", rate=Decimal("10"))
    p = _product(name="NoPromo", price_net_amount=Decimal("80.00"), tax_class=tc)

    _add_item(client, p)
    resp = client.get(CART_URL)
    assert resp.status_code == 200

    pricing = resp.json()["items"][0]["pricing"]
    assert pricing["undiscounted"] == pricing["discounted"]
    assert pricing["discount"]["amount_net"] == "0.00"
    assert pricing["discount"]["promotion_code"] is None


@pytest.mark.django_db
def test_cart_totals_without_promotion_discount_is_zero():
    """Cart totals must show zero total_discount when no promotion applies."""
    u = _user("npTotals")
    client = _auth_client(u)
    tc = _tax_class(code="npt_std", rate=Decimal("0"))
    p = _product(name="NpTotals", price_net_amount=Decimal("100.00"), tax_class=tc)

    _add_item(client, p, quantity=2)
    resp = client.get(CART_URL)
    totals = resp.json()["totals"]

    assert totals["total_discount"] == "0.00"
    # subtotal_undiscounted == subtotal_discounted
    assert totals["subtotal_undiscounted"] == totals["subtotal_discounted"]


# ---------------------------------------------------------------------------
# Product-targeted promotion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_product_promotion_reduces_cart_item_discounted_net():
    """A product-targeted 10 % promotion must reduce discounted net correctly."""
    u = _user("prodPromo")
    client = _auth_client(u)
    tc = _tax_class(code="pp_std", rate=Decimal("23"))
    p = _product(name="ProdPromo", price_net_amount=Decimal("100.00"), tax_class=tc)
    promo = _promotion(code="cart-pp-10", value=Decimal("10"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    _add_item(client, p)
    resp = client.get(CART_URL)
    assert resp.status_code == 200

    pricing = resp.json()["items"][0]["pricing"]
    assert pricing["undiscounted"]["net"] == "100.00"
    assert pricing["discounted"]["net"] == "90.00"
    assert pricing["discount"]["amount_net"] == "10.00"
    assert pricing["discount"]["promotion_code"] == "cart-pp-10"
    assert pricing["discount"]["promotion_type"] == "PERCENT"


# ---------------------------------------------------------------------------
# Category-targeted promotion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_category_promotion_reduces_cart_item_discounted_pricing():
    """A category-targeted promotion must apply to cart items in that category."""
    u = _user("catPromo")
    client = _auth_client(u)
    tc = _tax_class(code="cp_std", rate=Decimal("10"))
    cat = _category("Electronics")
    p = _product(name="Gadget", price_net_amount=Decimal("200.00"), tax_class=tc, category=cat)
    promo = _promotion(code="cart-cat-20", value=Decimal("20"))
    PromotionCategory.objects.create(promotion=promo, category=cat)

    _add_item(client, p)
    resp = client.get(CART_URL)
    assert resp.status_code == 200

    pricing = resp.json()["items"][0]["pricing"]
    # 20 % off 200 → discounted net = 160
    assert pricing["undiscounted"]["net"] == "200.00"
    assert pricing["discounted"]["net"] == "160.00"
    assert pricing["discount"]["amount_net"] == "40.00"


# ---------------------------------------------------------------------------
# Tax from discounted NET
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tax_calculated_from_discounted_net_not_undiscounted():
    """Tax in the discounted tier must be calculated from the post-discount NET.

    10 % off 100 EUR net → discounted net = 90 EUR.
    With 23 % tax: discounted gross = 90 × 1.23 = 110.70, tax = 20.70.
    Undiscounted: gross = 123.00, tax = 23.00.
    """
    u = _user("taxCheck")
    client = _auth_client(u)
    tc = _tax_class(code="cart_tax_check", rate=Decimal("23"))
    p = _product(name="TaxCheck", price_net_amount=Decimal("100.00"), tax_class=tc)
    promo = _promotion(code="cart-tax-10", value=Decimal("10"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    _add_item(client, p)
    resp = client.get(CART_URL)
    assert resp.status_code == 200

    pricing = resp.json()["items"][0]["pricing"]
    assert pricing["discounted"]["net"] == "90.00"
    assert pricing["discounted"]["gross"] == "110.70"
    assert pricing["discounted"]["tax"] == "20.70"
    assert pricing["undiscounted"]["gross"] == "123.00"
    assert pricing["undiscounted"]["tax"] == "23.00"


# ---------------------------------------------------------------------------
# Cart totals aggregation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cart_totals_aggregate_across_multiple_items():
    """Cart totals must be the correctly accumulated sum of all line totals.

    Setup:
    - Item A: net=100 EUR, 0 % tax, qty=2 → line_gross = 200 EUR
    - Item B: net=50 EUR, 0 % tax, qty=1 → line_gross = 50 EUR
    - No promotions → total_gross = 250 EUR
    """
    u = _user("multiItem")
    client = _auth_client(u)
    p_a = _product(name="ItemA", price_net_amount=Decimal("100.00"))
    p_b = _product(name="ItemB", price_net_amount=Decimal("50.00"))

    _add_item(client, p_a, quantity=2)
    _add_item(client, p_b, quantity=1)

    resp = client.get(CART_URL)
    assert resp.status_code == 200

    totals = resp.json()["totals"]
    assert totals["total_gross"] == "250.00"
    assert totals["subtotal_undiscounted"] == "250.00"
    assert totals["subtotal_discounted"] == "250.00"
    assert totals["total_discount"] == "0.00"
    assert totals["item_count"] == 3


@pytest.mark.django_db
def test_cart_totals_discount_aggregated_with_promotion():
    """total_discount must reflect sum of all per-line discounts × quantity.

    Setup:
    - Product: net=100 EUR, 0 % tax, 10 % promotion, qty=3
    - undiscounted_gross = 100 × 3 = 300
    - discounted_gross   =  90 × 3 = 270
    - total_discount     =  10 × 3 =  30
    """
    u = _user("multiDisc")
    client = _auth_client(u)
    p = _product(name="BulkDisc", price_net_amount=Decimal("100.00"))
    promo = _promotion(code="cart-bulk-10", value=Decimal("10"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    _add_item(client, p, quantity=3)
    resp = client.get(CART_URL)
    totals = resp.json()["totals"]

    assert totals["subtotal_undiscounted"] == "300.00"
    assert totals["subtotal_discounted"] == "270.00"
    assert totals["total_discount"] == "30.00"
    assert totals["total_gross"] == "270.00"
    assert totals["item_count"] == 3


@pytest.mark.django_db
def test_cart_totals_include_tax():
    """total_tax should reflect sum of discounted tax across all lines × quantity.

    Setup:
    - Product: net=100 EUR, 23 % tax, no promotion, qty=2
    - tax per unit = 23 EUR → total_tax = 46 EUR
    """
    u = _user("taxTotals")
    client = _auth_client(u)
    tc = _tax_class(code="cart_tax_tot", rate=Decimal("23"))
    p = _product(name="Taxed", price_net_amount=Decimal("100.00"), tax_class=tc)

    _add_item(client, p, quantity=2)
    resp = client.get(CART_URL)
    totals = resp.json()["totals"]

    assert totals["total_tax"] == "46.00"
    assert totals["total_gross"] == "246.00"
    assert totals["currency"] == "EUR"


@pytest.mark.django_db
def test_cart_totals_structure_complete():
    """totals must expose all required keys."""
    u = _user("totalsStruct")
    client = _auth_client(u)
    p = _product(name="Struct2", price_net_amount=Decimal("30.00"))

    _add_item(client, p)
    resp = client.get(CART_URL)
    totals = resp.json()["totals"]

    required_keys = {
        "subtotal_undiscounted",
        "subtotal_discounted",
        "total_discount",
        "total_tax",
        "total_gross",
        "currency",
        "item_count",
    }
    assert required_keys <= set(totals.keys())


# ---------------------------------------------------------------------------
# Existing item fields preserved (backward compatibility)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cart_item_legacy_fields_still_present():
    """Adding pricing must not remove the existing item fields."""
    u = _user("legacyFields")
    client = _auth_client(u)
    p = _product(name="LegacyCheck", price_net_amount=Decimal("15.00"))

    _add_item(client, p, quantity=2)
    resp = client.get(CART_URL)
    item = resp.json()["items"][0]

    assert "id" in item
    assert "product" in item
    assert "quantity" in item
    assert item["quantity"] == 2
    assert "price_at_add_time" in item


# ---------------------------------------------------------------------------
# Unmigrated product (no price_net_amount) — safe null pricing
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cart_item_unmigrated_product_pricing_is_null():
    """Cart item for a product with no price_net_amount must return pricing=null safely."""
    u = _user("legacy")
    client = _auth_client(u)
    # Product without price_net_amount — legacy / not yet migrated
    p = _product(name="LegacyProduct", price_net_amount=None)

    _add_item(client, p)
    resp = client.get(CART_URL)
    assert resp.status_code == 200

    item = resp.json()["items"][0]
    assert item["pricing"] is None
