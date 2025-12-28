import pytest
from rest_framework.test import APIClient
from products.models import Product


@pytest.mark.django_db
def test_products_list_returns_only_active_products():
    client = APIClient()

    active_product = Product.objects.create(
        name="Active Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )
    inactive_product = Product.objects.create(
        name="Inactive Product",
        price=100,
        stock_quantity=10,
        is_active=False,
    )

    response = client.get("/api/v1/products/")

    assert response.status_code == 200
    data = response.json()

    returned_names = {item["name"] for item in data}

    # endpoint vrátil aktivní produkt
    assert active_product.name in returned_names

    # endpoint nevrátil neaktivní produkt
    assert inactive_product.name not in returned_names


@pytest.mark.django_db
def test_product_detail_returns_product():
    product = Product.objects.create(
        name="Product A",
        price=50,
        stock_quantity=5,
        is_active=True,
    )

    client = APIClient()
    response = client.get(f"/api/v1/products/{product.id}/")

    assert response.status_code == 200
    assert response.json()["name"] == "Product A"
