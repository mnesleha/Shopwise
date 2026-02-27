import pytest
from rest_framework.test import APIClient
from products.models import Product
from categories.models import Category


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


@pytest.mark.django_db
def test_products_list_can_be_filtered_by_category():
    client = APIClient()

    c1 = Category.objects.create(name="Electronics")
    c2 = Category.objects.create(name="Accessories")

    p1 = Product.objects.create(name="Mouse", price=10, stock_quantity=5, is_active=True, category=c1)
    Product.objects.create(name="Cable", price=5, stock_quantity=5, is_active=True, category=c2)

    response = client.get(f"/api/v1/products/?category={c1.id}")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == p1.id
    assert data[0]["category_id"] == c1.id