"""API tests for Phase 2 catalogue pricing integration with line-level promotions.

Covers:
- product without promotion returns undiscounted == discounted
- product-level promotion reduces discounted net/gross/tax correctly
- category-level promotion reduces discounted net/gross/tax correctly
- tax is always calculated from discounted NET (not undiscounted NET)
- fixed discount reflected in gross and tax correctly
- list and detail API return consistent pricing structure
- pricing works safely when price_net_amount is not set (null safety)
- discount sub-keys are zero/null when no promotion applies
- discount.percentage computed correctly
- both undiscounted and discounted tiers always present
"""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from categories.models import Category
from discounts.models import Promotion, PromotionAmountScope, PromotionCategory, PromotionProduct, PromotionType
from products.models import Product, TaxClass

LIST_URL = "/api/v1/products/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tax_class(*, code: str, rate=None) -> TaxClass:
    return TaxClass.objects.create(name=code.title(), code=code, rate=rate)


def _category(name: str = "Electronics") -> Category:
    return Category.objects.create(name=name)


def _product(
    *,
    name: str = "Test Product",
    price_net_amount=None,
    currency: str = "EUR",
    tax_class=None,
    category=None,
) -> Product:
    return Product.objects.create(
        name=name,
        price=price_net_amount if price_net_amount is not None else Decimal("9.99"),
        stock_quantity=5,
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
    amount_scope: str = PromotionAmountScope.GROSS,
) -> Promotion:
    return Promotion.objects.create(
        name=f"Promo {code}",
        code=code,
        type=promo_type,
        value=value,
        priority=priority,
        is_active=True,
        amount_scope=amount_scope,
    )


def _detail_url(pk: int) -> str:
    return f"/api/v1/products/{pk}/"


def _client() -> APIClient:
    return APIClient()


# ---------------------------------------------------------------------------
# No-promotion baseline: undiscounted == discounted
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_product_without_promotion_undiscounted_equals_discounted():
    """When no promotion applies, undiscounted and discounted tiers must be equal."""
    tc = _tax_class(code="base_std", rate=Decimal("23"))
    p = _product(name="Unpromoted", price_net_amount=Decimal("100.00"), tax_class=tc)

    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    assert pricing["undiscounted"] == pricing["discounted"]


@pytest.mark.django_db
def test_product_without_promotion_discount_amounts_are_zero():
    """discount.amount_net and amount_gross must be '0.00' with no promotion."""
    p = _product(name="NoDisco", price_net_amount=Decimal("50.00"))

    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    discount = resp.json()["pricing"]["discount"]

    assert discount["amount_net"] == "0.00"
    assert discount["amount_gross"] == "0.00"
    assert discount["promotion_code"] is None
    assert discount["promotion_type"] is None


# ---------------------------------------------------------------------------
# Product-level promotion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_product_targeted_promotion_reduces_discounted_net():
    """A 10 % product-targeted promotion must halve the discount on a 100 EUR net."""
    tc = _tax_class(code="prod_std", rate=Decimal("23"))
    p = _product(name="PromotedProduct", price_net_amount=Decimal("100.00"), tax_class=tc)
    promo = _promotion(code="prod-10pct", value=Decimal("10"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    assert pricing["undiscounted"]["net"] == "100.00"
    assert pricing["discounted"]["net"] == "90.00"
    assert pricing["discount"]["amount_net"] == "10.00"
    assert pricing["discount"]["promotion_code"] == "prod-10pct"


@pytest.mark.django_db
def test_product_targeted_promotion_consistent_list_and_detail():
    """List and detail must return identical pricing for the same product."""
    tc = _tax_class(code="cons_std", rate=Decimal("23"))
    p = _product(name="ConsistencyProd", price_net_amount=Decimal("80.00"), tax_class=tc)
    promo = _promotion(code="cons-promo", value=Decimal("20"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    list_resp = _client().get(LIST_URL)
    detail_resp = _client().get(_detail_url(p.id))

    assert list_resp.status_code == 200
    assert detail_resp.status_code == 200

    list_pricing = list_resp.json()["results"][0]["pricing"]
    detail_pricing = detail_resp.json()["pricing"]
    assert list_pricing == detail_pricing


# ---------------------------------------------------------------------------
# Category-level promotion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_category_targeted_promotion_reduces_discounted_pricing():
    """A category-targeted promotion must apply to products in that category."""
    tc = _tax_class(code="cat_std", rate=Decimal("10"))
    cat = _category("Gadgets")
    p = _product(name="Gadget", price_net_amount=Decimal("200.00"), tax_class=tc, category=cat)
    promo = _promotion(code="cat-20pct", value=Decimal("20"))
    PromotionCategory.objects.create(promotion=promo, category=cat)

    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    # 20 % off 200 → discounted net = 160
    assert pricing["undiscounted"]["net"] == "200.00"
    assert pricing["discounted"]["net"] == "160.00"
    assert pricing["discount"]["amount_net"] == "40.00"
    assert pricing["discount"]["promotion_code"] == "cat-20pct"


# ---------------------------------------------------------------------------
# Tax is computed on discounted NET
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tax_computed_from_discounted_net_not_undiscounted():
    """Tax in the discounted tier must be calculated from the post-discount NET.

    10 % discount on 100 EUR net → discounted net = 90 EUR.
    With 23 % tax: discounted gross = 90 * 1.23 = 110.70, tax = 20.70.
    Undiscounted gross = 100 * 1.23 = 123.00, tax = 23.00.
    """
    tc = _tax_class(code="tax_from_disco", rate=Decimal("23"))
    p = _product(name="TaxCheck", price_net_amount=Decimal("100.00"), tax_class=tc)
    promo = _promotion(code="tax-10pct", value=Decimal("10"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    assert pricing["undiscounted"]["net"] == "100.00"
    assert pricing["undiscounted"]["gross"] == "123.00"
    assert pricing["undiscounted"]["tax"] == "23.00"

    assert pricing["discounted"]["net"] == "90.00"
    assert pricing["discounted"]["gross"] == "110.70"
    assert pricing["discounted"]["tax"] == "20.70"


@pytest.mark.django_db
def test_fixed_discount_reflected_in_gross_and_tax():
    """A FIXED+GROSS discount deducts from the gross price; net is back-computed.

    Setup: net=20 EUR, tax=10% → gross=22 EUR.
    FIXED 5 EUR off GROSS:
      discounted_gross = 22 − 5 = 17.00
      discounted_net   = 17 / 1.10 = 15.45  (ROUND_HALF_UP)
      discounted_tax   = 17.00 − 15.45 = 1.55
      discount.amount_net   = 20.00 − 15.45 = 4.55
      discount.amount_gross = 22.00 − 17.00 = 5.00
    """
    tc = _tax_class(code="fixed_tax", rate=Decimal("10"))
    p = _product(name="FixedDiscount", price_net_amount=Decimal("20.00"), tax_class=tc)
    promo = _promotion(
        code="fixed-5",
        promo_type=PromotionType.FIXED,
        value=Decimal("5.00"),
        amount_scope=PromotionAmountScope.GROSS,
    )
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    assert pricing["undiscounted"]["net"] == "20.00"
    assert pricing["undiscounted"]["gross"] == "22.00"

    assert pricing["discounted"]["net"] == "15.45"
    assert pricing["discounted"]["gross"] == "17.00"
    assert pricing["discounted"]["tax"] == "1.55"

    assert pricing["discount"]["amount_net"] == "4.55"
    assert pricing["discount"]["amount_gross"] == "5.00"
    assert pricing["discount"]["promotion_type"] == "FIXED"
    assert pricing["discount"]["amount_scope"] == "GROSS"


@pytest.mark.django_db
def test_fixed_net_discount_reflected_in_gross_and_tax():
    """A FIXED+NET discount deducts from the net price directly (explicit amount_scope=NET).

    Setup: net=20 EUR, tax=10%.
    FIXED 5 EUR off NET:
      discounted_net   = 20 − 5 = 15.00
      discounted_gross = 15 * 1.10 = 16.50
      discounted_tax   = 16.50 − 15.00 = 1.50
      discount.amount_net   = 5.00
      discount.amount_gross = 22.00 − 16.50 = 5.50
    """
    tc = _tax_class(code="fixed_net_tax", rate=Decimal("10"))
    p = _product(name="FixedNetDiscount", price_net_amount=Decimal("20.00"), tax_class=tc)
    promo = _promotion(
        code="fixed-net-5",
        promo_type=PromotionType.FIXED,
        value=Decimal("5.00"),
        amount_scope=PromotionAmountScope.NET,
    )
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    assert pricing["discounted"]["net"] == "15.00"
    assert pricing["discounted"]["gross"] == "16.50"
    assert pricing["discounted"]["tax"] == "1.50"

    assert pricing["discount"]["amount_net"] == "5.00"
    assert pricing["discount"]["amount_gross"] == "5.50"
    assert pricing["discount"]["promotion_type"] == "FIXED"
    assert pricing["discount"]["amount_scope"] == "NET"


# ---------------------------------------------------------------------------
# discount.percentage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_discount_percentage_computed_correctly_for_percent_promotion():
    """discount.percentage must equal the effective percentage off the undiscounted net."""
    p = _product(name="PctCheck", price_net_amount=Decimal("100.00"))
    promo = _promotion(code="pct-15", value=Decimal("15"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    discount = resp.json()["pricing"]["discount"]
    assert discount["percentage"] == "15.00"


@pytest.mark.django_db
def test_discount_percentage_for_fixed_discount():
    """discount.percentage for a FIXED type is derived from effective net reduction."""
    # 5 EUR off 20 EUR = 25 %
    p = _product(name="FixedPct", price_net_amount=Decimal("20.00"))
    promo = _promotion(code="fixed-pct-check", promo_type=PromotionType.FIXED, value=Decimal("5.00"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    discount = resp.json()["pricing"]["discount"]
    assert discount["percentage"] == "25.00"


@pytest.mark.django_db
def test_no_promo_discount_percentage_is_zero():
    """discount.percentage must be '0' when no promotion applies."""
    p = _product(name="NoPcr", price_net_amount=Decimal("50.00"))

    resp = _client().get(_detail_url(p.id))
    discount = resp.json()["pricing"]["discount"]
    assert discount["percentage"] == "0"


# ---------------------------------------------------------------------------
# Null-safety for unmigrated products
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_null_for_unmigrated_product_with_promotion_in_db():
    """pricing must still be null when price_net_amount is unset, even with a promotion."""
    promo = _promotion(code="orphan", value=Decimal("10"))
    p = _product(name="Legacy", price_net_amount=None)
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    assert resp.json()["pricing"] is None


# ---------------------------------------------------------------------------
# Structure completeness
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_structure_complete_without_promotion():
    """All three top-level pricing keys must be present even with no promotion."""
    p = _product(name="Complete", price_net_amount=Decimal("30.00"))

    resp = _client().get(_detail_url(p.id))
    pricing = resp.json()["pricing"]

    assert set(pricing.keys()) >= {"undiscounted", "discounted", "discount"}
    for tier in ("undiscounted", "discounted"):
        assert {"net", "gross", "tax", "currency", "tax_rate"} <= set(pricing[tier].keys())
    discount_keys = {"amount_net", "amount_gross", "percentage", "promotion_code", "promotion_type", "amount_scope"}
    assert discount_keys <= set(pricing["discount"].keys())


@pytest.mark.django_db
def test_pricing_structure_complete_with_promotion():
    """All three top-level pricing keys must be present with an active promotion."""
    p = _product(name="WithPromo", price_net_amount=Decimal("50.00"))
    promo = _promotion(code="struct-check", value=Decimal("10"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    pricing = resp.json()["pricing"]

    assert set(pricing.keys()) >= {"undiscounted", "discounted", "discount"}
    for tier in ("undiscounted", "discounted"):
        assert {"net", "gross", "tax", "currency", "tax_rate"} <= set(pricing[tier].keys())
    discount_keys = {"amount_net", "amount_gross", "percentage", "promotion_code", "promotion_type", "amount_scope"}
    assert discount_keys <= set(pricing["discount"].keys())


# ---------------------------------------------------------------------------
# amount_scope field
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_amount_scope_is_null_when_no_promotion():
    """discount.amount_scope must be null when no promotion applies."""
    p = _product(name="NoPromoScope", price_net_amount=Decimal("30.00"))

    resp = _client().get(_detail_url(p.id))
    assert resp.json()["pricing"]["discount"]["amount_scope"] is None


@pytest.mark.django_db
def test_amount_scope_is_null_for_percent_promotion():
    """discount.amount_scope must be null for PERCENT promotions."""
    p = _product(name="PctScope", price_net_amount=Decimal("40.00"))
    promo = _promotion(code="pct-scope", value=Decimal("10"))
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    assert resp.json()["pricing"]["discount"]["amount_scope"] is None


@pytest.mark.django_db
def test_amount_scope_gross_for_fixed_gross_promotion():
    """discount.amount_scope must be 'GROSS' for FIXED+GROSS (the default)."""
    p = _product(name="GrossScope", price_net_amount=Decimal("50.00"))
    promo = _promotion(
        code="gross-scope",
        promo_type=PromotionType.FIXED,
        value=Decimal("10.00"),
        amount_scope=PromotionAmountScope.GROSS,
    )
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    assert resp.json()["pricing"]["discount"]["amount_scope"] == "GROSS"


@pytest.mark.django_db
def test_amount_scope_net_for_fixed_net_promotion():
    """discount.amount_scope must be 'NET' for explicit FIXED+NET."""
    p = _product(name="NetScope", price_net_amount=Decimal("50.00"))
    promo = _promotion(
        code="net-scope",
        promo_type=PromotionType.FIXED,
        value=Decimal("10.00"),
        amount_scope=PromotionAmountScope.NET,
    )
    PromotionProduct.objects.create(promotion=promo, product=p)

    resp = _client().get(_detail_url(p.id))
    assert resp.json()["pricing"]["discount"]["amount_scope"] == "NET"
