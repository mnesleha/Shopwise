import pytest
from rest_framework.test import APIClient
from products.models import Product


@pytest.mark.django_db
def test_create_order():
    client = APIClient()
    response = client.post("/api/v1/orders/")

    assert response.status_code == 201
    assert response.json()["status"] == "CREATED"


@pytest.mark.django_db
def test_add_item_to_order():
    product = Product.objects.create(
        name="Product A",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    client = APIClient()
    order_response = client.post("/api/v1/orders/")
    order_id = order_response.json()["id"]

    response = client.post(
        f"/api/v1/orders/{order_id}/items/",
        {
            "product_id": product.id,
            "quantity": 2,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["quantity"] == 2
    assert response.json()["price_at_order_time"] == "100.00"


@pytest.mark.django_db
def test_order_detail_returns_items_and_total():
    product = Product.objects.create(
        name="Product A",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    client = APIClient()
    order_id = client.post("/api/v1/orders/").json()["id"]

    client.post(
        f"/api/v1/orders/{order_id}/items/",
        {
            "product_id": product.id,
            "quantity": 2,
        },
        format="json",
    )

    response = client.get(f"/api/v1/orders/{order_id}/")

    print(response.json())
    assert response.status_code == 200
    assert response.json()["total_price"] == "200.00"
