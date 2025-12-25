import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from products.models import Product


@pytest.fixture
def user():
    return User.objects.create_user(
        username="testuser",
        password="pass1234",
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def product():
    return Product.objects.create(
        name="Test Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )


def create_order_via_checkout(auth_client, product, quantity=2):
    # ensure cart exists
    auth_client.get("/api/v1/cart/")

    # add item
    auth_client.post(
        "/api/v1/cart/items/",
        {
            "product_id": product.id,
            "quantity": quantity,
        },
        format="json",
    )

    # checkout
    response = auth_client.post("/api/v1/cart/checkout/")
    return response.json()
