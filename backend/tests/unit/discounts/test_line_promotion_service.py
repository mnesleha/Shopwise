"""Unit tests for Phase 2 line-level promotion resolver.

Covers:
- Product-targeted promotion applies
- Category-targeted promotion applies
- Inactive promotion is ignored
- Promotion before active_from is ignored
- Promotion after active_to is ignored
- Higher priority wins over lower priority
- Stable tie-breaker (lowest id) when priorities are equal
- PERCENT discount calculates correctly from net
- FIXED discount calculates correctly from net
- FIXED discount cannot reduce discounted net below zero
- No applicable promotion returns safe no-discount result
- Product without a category only matched by product targets (not category targets)
- discounted_net is always non-negative
"""

from decimal import Decimal

import pytest
from django.utils.timezone import now
from prices import Money

from categories.models import Category
from discounts.models import Promotion, PromotionAmountScope, PromotionCategory, PromotionProduct, PromotionType
from discounts.services.line_promotion import LinePromotionResult, resolve_line_promotion
from products.models import Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_category(name: str = "Electronics") -> Category:
    return Category.objects.create(name=name)


def make_product(
    name: str = "Test Product",
    category: Category | None = None,
) -> Product:
    return Product.objects.create(
        name=name,
        price=Decimal("10.00"),
        stock_quantity=1,
        price_net_amount=Decimal("10.00"),
        currency="EUR",
        category=category,
    )


def make_promotion(
    code: str = "promo",
    promo_type: str = PromotionType.PERCENT,
    value: Decimal = Decimal("10"),
    priority: int = 0,
    is_active: bool = True,
    active_from=None,
    active_to=None,
    amount_scope: str = PromotionAmountScope.GROSS,
) -> Promotion:
    return Promotion.objects.create(
        name=f"Promo {code}",
        code=code,
        type=promo_type,
        value=value,
        priority=priority,
        is_active=is_active,
        active_from=active_from,
        active_to=active_to,
        amount_scope=amount_scope,
    )


def target_product(promotion: Promotion, product: Product) -> PromotionProduct:
    return PromotionProduct.objects.create(promotion=promotion, product=product)


def target_category(promotion: Promotion, category: Category) -> PromotionCategory:
    return PromotionCategory.objects.create(promotion=promotion, category=category)


# ---------------------------------------------------------------------------
# No-promotion baseline
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_promotion_returns_zero_discount():
    """When no promotion applies, result carries no discount and discounted_net equals original."""
    product = make_product()

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("49.99"),
        currency="EUR",
    )

    assert isinstance(result, LinePromotionResult)
    assert result.promotion is None
    assert result.promotion_code is None
    assert result.promotion_type is None
    assert result.amount_scope is None
    assert result.discount_net == Money(Decimal("0.00"), "EUR")
    assert result.discounted_net == result.original_net
    assert result.original_net == Money(Decimal("49.99"), "EUR")


# ---------------------------------------------------------------------------
# Product targeting
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_product_targeted_promotion_applies():
    product = make_product()
    promo = make_promotion(code="prod-promo", promo_type=PromotionType.PERCENT, value=Decimal("10"))
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
    )

    assert result.promotion == promo
    assert result.discount_net == Money(Decimal("10.00"), "EUR")
    assert result.discounted_net == Money(Decimal("90.00"), "EUR")


@pytest.mark.django_db
def test_product_without_category_not_matched_by_category_target():
    """A promotion targeting a category must not apply to a product without a category."""
    category = make_category()
    product = make_product(category=None)  # no category
    promo = make_promotion(code="cat-only")
    target_category(promo, category)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
    )

    assert result.promotion is None


# ---------------------------------------------------------------------------
# Category targeting
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_category_targeted_promotion_applies():
    category = make_category()
    product = make_product(category=category)
    promo = make_promotion(code="cat-promo", promo_type=PromotionType.PERCENT, value=Decimal("20"))
    target_category(promo, category)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("50.00"),
        currency="EUR",
    )

    assert result.promotion == promo
    assert result.discount_net == Money(Decimal("10.00"), "EUR")
    assert result.discounted_net == Money(Decimal("40.00"), "EUR")


# ---------------------------------------------------------------------------
# Activity / date window filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_inactive_promotion_is_ignored():
    product = make_product()
    promo = make_promotion(code="inactive", is_active=False)
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
    )

    assert result.promotion is None


@pytest.mark.django_db
def test_promotion_before_active_from_is_ignored():
    today = now().date()
    future = today.replace(year=today.year + 1)
    product = make_product()
    promo = make_promotion(code="future", active_from=future)
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
    )

    assert result.promotion is None


@pytest.mark.django_db
def test_promotion_after_active_to_is_ignored():
    today = now().date()
    past = today.replace(year=today.year - 1)
    product = make_product()
    promo = make_promotion(code="expired", active_to=past)
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
    )

    assert result.promotion is None


@pytest.mark.django_db
def test_promotion_on_exact_active_from_date_applies():
    today = now().date()
    product = make_product()
    promo = make_promotion(code="starts-today", active_from=today)
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
    )

    assert result.promotion == promo


@pytest.mark.django_db
def test_promotion_on_exact_active_to_date_applies():
    today = now().date()
    product = make_product()
    promo = make_promotion(code="ends-today", active_to=today)
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
    )

    assert result.promotion == promo


# ---------------------------------------------------------------------------
# Winner selection — priority and tie-breaker
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_higher_priority_wins():
    product = make_product()

    low = make_promotion(code="low-prio", value=Decimal("5"), priority=1)
    high = make_promotion(code="high-prio", value=Decimal("50"), priority=10)
    target_product(low, product)
    target_product(high, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
    )

    assert result.promotion == high
    assert result.promotion_code == "high-prio"


@pytest.mark.django_db
def test_stable_tie_breaker_when_equal_priority():
    """When two promotions share the same priority, the one with the lower id wins."""
    product = make_product()

    first = make_promotion(code="first", value=Decimal("5"), priority=5)
    second = make_promotion(code="second", value=Decimal("50"), priority=5)
    target_product(first, product)
    target_product(second, product)

    # first has a lower id because it was created first.
    assert first.id < second.id

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
    )

    assert result.promotion == first


# ---------------------------------------------------------------------------
# Discount calculation — PERCENT
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_percent_discount_calculation():
    product = make_product()
    promo = make_promotion(code="pct", promo_type=PromotionType.PERCENT, value=Decimal("15"))
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("200.00"),
        currency="EUR",
    )

    assert result.discount_net == Money(Decimal("30.00"), "EUR")
    assert result.discounted_net == Money(Decimal("170.00"), "EUR")


@pytest.mark.django_db
def test_percent_discount_rounding():
    """10 % of 9.99 = 0.999 → rounds to 1.00 (ROUND_HALF_UP)."""
    product = make_product()
    promo = make_promotion(code="pct-round", promo_type=PromotionType.PERCENT, value=Decimal("10"))
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("9.99"),
        currency="EUR",
    )

    assert result.discount_net == Money(Decimal("1.00"), "EUR")
    assert result.discounted_net == Money(Decimal("8.99"), "EUR")


@pytest.mark.django_db
def test_100_percent_discount_results_in_zero_net():
    product = make_product()
    promo = make_promotion(code="full-pct", promo_type=PromotionType.PERCENT, value=Decimal("100"))
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("49.99"),
        currency="EUR",
    )

    assert result.discounted_net == Money(Decimal("0.00"), "EUR")


# ---------------------------------------------------------------------------
# Discount calculation — FIXED
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fixed_discount_calculation():
    """FIXED+GROSS with no tax is identical to FIXED+NET (tax_rate=0 → multiplier=1)."""
    product = make_product()
    promo = make_promotion(
        code="fixed",
        promo_type=PromotionType.FIXED,
        value=Decimal("5.00"),
        amount_scope=PromotionAmountScope.GROSS,
    )
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("20.00"),
        currency="EUR",
        tax_rate=Decimal("0"),
    )

    assert result.discount_net == Money(Decimal("5.00"), "EUR")
    assert result.discounted_net == Money(Decimal("15.00"), "EUR")
    assert result.amount_scope == PromotionAmountScope.GROSS


@pytest.mark.django_db
def test_fixed_gross_discount_with_tax():
    """FIXED+GROSS with a nonzero tax rate back-computes the net discount correctly.

    net=100 EUR, tax_rate=25%:
      undiscounted_gross = 100 * 1.25 = 125.00
      gross_discount     = min(25, 125) = 25.00
      discounted_gross   = 125 - 25 = 100.00
      discounted_net     = 100 / 1.25 = 80.00
      discount_net       = 100 - 80 = 20.00
    """
    product = make_product()
    promo = make_promotion(
        code="fixed-gross-tax",
        promo_type=PromotionType.FIXED,
        value=Decimal("25.00"),
        amount_scope=PromotionAmountScope.GROSS,
    )
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="EUR",
        tax_rate=Decimal("25"),
    )

    assert result.discount_net == Money(Decimal("20.00"), "EUR")
    assert result.discounted_net == Money(Decimal("80.00"), "EUR")
    assert result.amount_scope == PromotionAmountScope.GROSS


@pytest.mark.django_db
def test_fixed_net_discount_explicit():
    """FIXED+NET subtracts the fixed amount from the net price directly."""
    product = make_product()
    promo = make_promotion(
        code="fixed-net",
        promo_type=PromotionType.FIXED,
        value=Decimal("5.00"),
        amount_scope=PromotionAmountScope.NET,
    )
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("20.00"),
        currency="EUR",
        tax_rate=Decimal("23"),  # tax_rate ignored for NET scope
    )

    assert result.discount_net == Money(Decimal("5.00"), "EUR")
    assert result.discounted_net == Money(Decimal("15.00"), "EUR")
    assert result.amount_scope == PromotionAmountScope.NET


@pytest.mark.django_db
def test_fixed_discount_cannot_reduce_net_below_zero():
    """A FIXED discount larger than the net price must be capped at net → discounted_net = 0."""
    product = make_product()
    promo = make_promotion(code="huge-fixed", promo_type=PromotionType.FIXED, value=Decimal("999.00"))
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("9.99"),
        currency="EUR",
    )

    assert result.discounted_net == Money(Decimal("0.00"), "EUR")
    # discount_net must not exceed original
    assert result.discount_net == result.original_net


@pytest.mark.django_db
def test_fixed_discount_equal_to_net_results_in_zero():
    product = make_product()
    promo = make_promotion(code="exact-fixed", promo_type=PromotionType.FIXED, value=Decimal("50.00"))
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("50.00"),
        currency="EUR",
    )

    assert result.discounted_net == Money(Decimal("0.00"), "EUR")


# ---------------------------------------------------------------------------
# Result metadata
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_carries_promotion_code_and_type():
    product = make_product()
    promo = make_promotion(
        code="meta-check",
        promo_type=PromotionType.FIXED,
        value=Decimal("3.00"),
        amount_scope=PromotionAmountScope.GROSS,
    )
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("30.00"),
        currency="EUR",
    )

    assert result.promotion_code == "meta-check"
    assert result.promotion_type == PromotionType.FIXED
    assert result.amount_scope == PromotionAmountScope.GROSS


@pytest.mark.django_db
def test_currency_is_propagated_to_result():
    product = make_product()
    promo = make_promotion(code="usd-promo", promo_type=PromotionType.PERCENT, value=Decimal("10"))
    target_product(promo, product)

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("100.00"),
        currency="USD",
    )

    assert result.currency == "USD"
    assert result.original_net.currency == "USD"
    assert result.discount_net.currency == "USD"
    assert result.discounted_net.currency == "USD"
