import pytest
from django.core.exceptions import ValidationError
from django.utils.timezone import now, timedelta
from discounts.models import Discount
from products.models import Product
from categories.models import Category
from django.utils.timezone import now, timedelta
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_discount_is_valid_only_within_date_range():

    discount = Discount.objects.create(
        name="Summer Sale",
        discount_type="PERCENT",
        value=10,
        valid_from=now() - timedelta(days=1),
        valid_to=now() + timedelta(days=1),
        is_active=True,
    )

    assert discount.is_valid() is True


@pytest.mark.django_db
def test_discount_with_invalid_date_range_is_invalid():

    discount = Discount(
        name="Broken Discount",
        discount_type="PERCENT",
        value=10,
        valid_from=now() + timedelta(days=1),
        valid_to=now(),
        is_active=True,
    )

    with pytest.raises(ValidationError):
        discount.full_clean()


@pytest.mark.regression
@pytest.mark.django_db
def test_inactive_discount_is_not_valid():

    discount = Discount.objects.create(
        name="Inactive Discount",
        discount_type="PERCENT",
        value=20,
        valid_from=now() - timedelta(days=1),
        valid_to=now() + timedelta(days=1),
        is_active=False,
    )

    assert discount.is_valid() is False


@pytest.mark.django_db
def test_discount_without_target_is_invalid():

    discount = Discount(
        name="No Target Discount",
        discount_type="PERCENT",
        value=10,
        valid_from=now() - timedelta(days=1),
        valid_to=now() + timedelta(days=1),
        is_active=True,
    )

    with pytest.raises(ValidationError):
        discount.full_clean()


@pytest.mark.django_db
def test_discount_cannot_target_product_and_category_at_once():

    category = Category.objects.create(name="Electronics")

    product = Product.objects.create(
        name="Phone",
        price=1000,
        stock_quantity=10,
        is_active=True,
    )

    discount = Discount(
        name="Conflicting Discount",
        discount_type="PERCENT",
        value=10,
        valid_from=now() - timedelta(days=1),
        valid_to=now() + timedelta(days=1),
        is_active=True,
        product=product,
        category=category,
    )

    with pytest.raises(ValidationError):
        discount.full_clean()


@pytest.mark.django_db
def test_discount_with_zero_value_is_invalid():

    discount = Discount(
        name="Zero Discount",
        discount_type="PERCENT",
        value=0,
        valid_from=now() - timedelta(days=1),
        valid_to=now() + timedelta(days=1),
        is_active=True,
    )

    with pytest.raises(ValidationError):
        discount.full_clean()
