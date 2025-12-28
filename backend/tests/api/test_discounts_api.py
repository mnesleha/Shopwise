import pytest
from rest_framework.test import APIClient
from discounts.models import Discount
from products.models import Product
from datetime import date


import pytest
from datetime import date
from rest_framework.test import APIClient
from products.models import Product
from discounts.models import Discount


@pytest.mark.django_db
def test_discounts_return_only_valid_product_discounts():
    product = Product.objects.create(
        name="Product A",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    valid_discount = Discount.objects.create(
        product=product,
        discount_type=Discount.PERCENT,
        value=10,
        is_active=True,
        valid_from=date.today(),
        valid_to=date.today(),
    )

    inactive_discount = Discount.objects.create(
        product=product,
        discount_type=Discount.PERCENT,
        value=20,
        is_active=False,
        valid_from=date.today(),
        valid_to=date.today(),
    )

    client = APIClient()
    response = client.get("/api/v1/discounts/")

    assert response.status_code == 200
    data = response.json()

    returned_ids = {item["id"] for item in data}

    # valid discount je vrácen
    assert valid_discount.id in returned_ids

    # inactive discount vrácen není
    assert inactive_discount.id not in returned_ids

    # product link control
    valid_item = next(item for item in data if item["id"] == valid_discount.id)
    assert valid_item["product"]["id"] == product.id
