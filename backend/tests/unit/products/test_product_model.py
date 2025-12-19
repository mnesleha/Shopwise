import pytest


@pytest.mark.django_db
def test_inactive_product_is_not_sellable():
    from products.models import Product

    product = Product.objects.create(
        name="iPhone",
        price=1000,
        stock_quantity=10,
        is_active=False,
    )

    assert product.is_sellable() is False
