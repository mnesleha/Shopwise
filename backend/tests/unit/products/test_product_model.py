import pytest
from django.core.exceptions import ValidationError
from products.models import Product


@pytest.mark.django_db
def test_inactive_product_is_not_sellable():

    product = Product.objects.create(
        name="iPhone",
        price=1000,
        stock_quantity=10,
        is_active=False,
    )

    assert product.is_sellable() is False


@pytest.mark.regression
@pytest.mark.django_db
def test_product_with_zero_stock_is_not_sellable():

    product = Product.objects.create(
        name="Out of stock product",
        price=1000,
        stock_quantity=0,
        is_active=True,
    )

    assert product.is_sellable() is False


@pytest.mark.django_db
def test_inactive_product_is_not_sellable_even_with_stock():

    product = Product.objects.create(
        name="Inactive product",
        price=1000,
        stock_quantity=10,
        is_active=False,
    )

    assert product.is_sellable() is False


@pytest.mark.django_db
def test_product_with_negative_stock_is_invalid():

    product = Product(
        name="Invalid stock product",
        price=1000,
        stock_quantity=-5,
        is_active=True,
    )

    with pytest.raises(ValidationError):
        product.full_clean()


@pytest.mark.django_db
def test_product_with_zero_price_is_invalid():

    product = Product(
        name="Free product",
        price=0,
        stock_quantity=10,
        is_active=True,
    )

    with pytest.raises(ValidationError):
        product.full_clean()


@pytest.mark.django_db
def test_product_with_negative_price_is_invalid():

    product = Product(
        name="Broken product",
        price=-100,
        stock_quantity=10,
        is_active=True,
    )

    with pytest.raises(ValidationError):
        product.full_clean()


@pytest.mark.django_db
def test_product_without_name_is_invalid():

    product = Product(
        name="",
        price=1000,
        stock_quantity=10,
        is_active=True,
    )

    with pytest.raises(ValidationError):
        product.full_clean()
