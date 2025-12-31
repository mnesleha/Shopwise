from decimal import Decimal
import pytest
from datetime import date

from api.services.pricing import calculate_price
from discounts.models import Discount
from products.models import Product


@pytest.mark.django_db
def test_fixed_discount_greater_than_price_clamps_to_zero():
    product = Product.objects.create(
        name="Cheap",
        price=Decimal("10.00"),
        stock_quantity=10,
        is_active=True,
    )

    discount = Discount.objects.create(
        product=product,
        discount_type=Discount.FIXED,
        value=Decimal("50.00"),
        is_active=True,
        valid_from=date.today(),
        valid_to=date.today(),
    )

    result = calculate_price(
        unit_price=product.price,
        quantity=1,
        discounts=[discount],
    )

    assert result.base_price == Decimal("10.00")
    assert result.final_price == Decimal("0.00")
    assert result.applied_discount == discount


@pytest.mark.django_db
def test_fixed_discount_has_priority_over_percent():
    product = Product.objects.create(
        name="Product",
        price=Decimal("100.00"),
        stock_quantity=10,
        is_active=True,
    )

    percent = Discount.objects.create(
        product=product,
        discount_type=Discount.PERCENT,
        value=Decimal("10.00"),
        is_active=True,
        valid_from=date.today(),
        valid_to=date.today(),
    )

    fixed = Discount.objects.create(
        product=product,
        discount_type=Discount.FIXED,
        value=Decimal("20.00"),
        is_active=True,
        valid_from=date.today(),
        valid_to=date.today(),
    )

    result = calculate_price(
        unit_price=product.price,
        quantity=1,
        discounts=[percent, fixed],
    )

    assert result.final_price == Decimal("80.00")
    assert result.applied_discount == fixed


@pytest.mark.django_db
def test_rounding_is_half_up_to_two_decimals():
    result = calculate_price(
        unit_price=Decimal("33.333"),
        quantity=3,
        discounts=[],
    )

    assert result.base_price == Decimal("99.999")
    assert result.final_price == Decimal("99.99")


def test_no_discount_returns_base_price():
    result = calculate_price(
        unit_price=Decimal("50.00"),
        quantity=2,
        discounts=[],
    )

    assert result.final_price == Decimal("100.00")
    assert result.applied_discount is None
