import pytest
from rest_framework.test import APIClient
from products.models import Product


@pytest.mark.django_db
def test_products_list_returns_only_active_products():
    client = APIClient()

    Product.objects.create(
        name="Active Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )
    Product.objects.create(
        name="Inactive Product",
        price=100,
        stock_quantity=10,
        is_active=False,
    )

    response = client.get("/api/v1/products/")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Active Product"


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
