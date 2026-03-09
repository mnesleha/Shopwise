"""Unit tests for Phase 2 Promotion domain models.

Covers:
- Promotion creation (happy path)
- Targeting via PromotionProduct and PromotionCategory
- Validation rules (value, percent ceiling, date window)
- Duplicate targeting protection
- is_currently_active() helper
- Admin registration sanity check
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils.timezone import now

from categories.models import Category
from discounts.admin import PromotionAdmin
from discounts.models import Promotion, PromotionCategory, PromotionProduct, PromotionType
from products.models import Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_product(name: str = "Test Product") -> Product:
    return Product.objects.create(name=name, price=10, stock_quantity=1)


def make_category(name: str = "Test Category") -> Category:
    return Category.objects.create(name=name)


def make_promotion(**kwargs) -> Promotion:
    defaults = {
        "name": "Summer Sale",
        "code": "summer-2026",
        "type": PromotionType.PERCENT,
        "value": 10,
        "priority": 5,
        "is_active": True,
    }
    defaults.update(kwargs)
    return Promotion.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Basic creation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_promotion_can_be_created():
    promo = make_promotion()

    assert promo.pk is not None
    assert promo.code == "summer-2026"
    assert str(promo) == "Summer Sale (summer-2026)"


@pytest.mark.django_db
def test_promotion_str_includes_code():
    promo = make_promotion(name="Winter Sale", code="winter-2026")
    assert "Winter Sale" in str(promo)
    assert "winter-2026" in str(promo)


@pytest.mark.django_db
def test_promotion_code_is_unique():
    make_promotion(code="unique-code")
    with pytest.raises(IntegrityError):
        # Must bypass clean() to hit the DB-level unique constraint.
        Promotion.objects.create(
            name="Duplicate",
            code="unique-code",
            type=PromotionType.PERCENT,
            value=5,
        )


# ---------------------------------------------------------------------------
# Targeting — PromotionProduct
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_promotion_product_target_can_be_created():
    promo = make_promotion()
    product = make_product()

    target = PromotionProduct.objects.create(promotion=promo, product=product)

    assert target.pk is not None
    assert promo.product_targets.count() == 1


@pytest.mark.django_db
def test_promotion_can_target_multiple_products():
    promo = make_promotion()
    p1 = make_product("Product A")
    p2 = make_product("Product B")

    PromotionProduct.objects.create(promotion=promo, product=p1)
    PromotionProduct.objects.create(promotion=promo, product=p2)

    assert promo.product_targets.count() == 2


@pytest.mark.django_db
def test_duplicate_product_target_is_prevented():
    promo = make_promotion()
    product = make_product()

    PromotionProduct.objects.create(promotion=promo, product=product)
    with pytest.raises(IntegrityError):
        PromotionProduct.objects.create(promotion=promo, product=product)


@pytest.mark.django_db
def test_promotion_product_str():
    promo = make_promotion(code="test-code")
    product = make_product("My Product")
    target = PromotionProduct.objects.create(promotion=promo, product=product)

    assert "test-code" in str(target)


# ---------------------------------------------------------------------------
# Targeting — PromotionCategory
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_promotion_category_target_can_be_created():
    promo = make_promotion()
    category = make_category()

    target = PromotionCategory.objects.create(promotion=promo, category=category)

    assert target.pk is not None
    assert promo.category_targets.count() == 1


@pytest.mark.django_db
def test_promotion_can_target_multiple_categories():
    promo = make_promotion()
    c1 = make_category("Electronics")
    c2 = make_category("Books")

    PromotionCategory.objects.create(promotion=promo, category=c1)
    PromotionCategory.objects.create(promotion=promo, category=c2)

    assert promo.category_targets.count() == 2


@pytest.mark.django_db
def test_duplicate_category_target_is_prevented():
    promo = make_promotion()
    category = make_category()

    PromotionCategory.objects.create(promotion=promo, category=category)
    with pytest.raises(IntegrityError):
        PromotionCategory.objects.create(promotion=promo, category=category)


@pytest.mark.django_db
def test_promotion_category_str():
    promo = make_promotion(code="test-code")
    category = make_category("My Category")
    target = PromotionCategory.objects.create(promotion=promo, category=category)

    assert "test-code" in str(target)


# ---------------------------------------------------------------------------
# Validation — value
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_promotion_value_must_be_positive():
    promo = Promotion(
        name="Bad Promo",
        code="bad-value",
        type=PromotionType.PERCENT,
        value=0,
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "value" in exc_info.value.message_dict


@pytest.mark.django_db
def test_promotion_negative_value_is_invalid():
    promo = Promotion(
        name="Negative Promo",
        code="neg-value",
        type=PromotionType.PERCENT,
        value=-5,
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "value" in exc_info.value.message_dict


@pytest.mark.django_db
def test_percent_promotion_value_cannot_exceed_100():
    promo = Promotion(
        name="Overblown Promo",
        code="over-100",
        type=PromotionType.PERCENT,
        value=101,
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "value" in exc_info.value.message_dict


@pytest.mark.django_db
def test_percent_promotion_value_exactly_100_is_valid():
    promo = Promotion(
        name="Full Promo",
        code="full-100",
        type=PromotionType.PERCENT,
        value=100,
    )
    # Should not raise.
    promo.full_clean()


@pytest.mark.django_db
def test_fixed_promotion_large_value_is_valid():
    """FIXED type is not bounded by 100."""
    promo = Promotion(
        name="Big Discount",
        code="big-fixed",
        type=PromotionType.FIXED,
        value=500,
    )
    promo.full_clean()


# ---------------------------------------------------------------------------
# Validation — active window
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_active_from_after_active_to_is_invalid():
    today = now().date()
    promo = Promotion(
        name="Bad Window",
        code="bad-window",
        type=PromotionType.PERCENT,
        value=10,
        active_from=today,
        active_to=today.replace(year=today.year - 1),
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "active_from" in exc_info.value.message_dict


@pytest.mark.django_db
def test_active_from_equals_active_to_is_valid():
    today = now().date()
    promo = Promotion(
        name="Single Day",
        code="single-day",
        type=PromotionType.PERCENT,
        value=10,
        active_from=today,
        active_to=today,
    )
    promo.full_clean()


@pytest.mark.django_db
def test_missing_both_dates_is_valid():
    promo = Promotion(
        name="No Window",
        code="no-window",
        type=PromotionType.PERCENT,
        value=10,
    )
    promo.full_clean()


# ---------------------------------------------------------------------------
# is_currently_active()
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_is_currently_active_no_dates():
    promo = make_promotion(is_active=True)
    assert promo.is_currently_active() is True


@pytest.mark.django_db
def test_is_currently_active_within_window():
    today = now().date()
    promo = make_promotion(
        code="in-window",
        active_from=today.replace(day=1),
        active_to=today.replace(day=28),
        is_active=True,
    )
    # Adjust to guarantee today falls inside the window.
    promo.active_from = today.replace(year=today.year - 1)
    promo.active_to = today.replace(year=today.year + 1)
    promo.save()

    assert promo.is_currently_active() is True


@pytest.mark.django_db
def test_is_not_active_when_disabled():
    promo = make_promotion(code="disabled", is_active=False)
    assert promo.is_currently_active() is False


@pytest.mark.django_db
def test_is_not_active_before_window():
    today = now().date()
    promo = make_promotion(
        code="future-promo",
        is_active=True,
        active_from=today.replace(year=today.year + 1),
    )
    assert promo.is_currently_active() is False


@pytest.mark.django_db
def test_is_not_active_after_window():
    today = now().date()
    promo = make_promotion(
        code="expired-promo",
        is_active=True,
        active_to=today.replace(year=today.year - 1),
    )
    assert promo.is_currently_active() is False


# ---------------------------------------------------------------------------
# Admin sanity
# ---------------------------------------------------------------------------


def test_promotion_admin_is_registered():
    """PromotionAdmin must be importable and instantiatable — basic wiring check."""
    site = AdminSite()
    admin_instance = PromotionAdmin(Promotion, site)
    assert admin_instance is not None


def test_promotion_admin_inlines_configured():
    from discounts.admin import PromotionCategoryInline, PromotionProductInline

    site = AdminSite()
    admin_instance = PromotionAdmin(Promotion, site)
    inline_models = [inline.model for inline in admin_instance.inlines]

    assert PromotionProduct in inline_models
    assert PromotionCategory in inline_models
