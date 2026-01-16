import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from carts.models import Cart
from products.models import Product


@pytest.mark.django_db
def test_get_cart_creates_new_cart(auth_client, user):
    # sanity check
    assert Cart.objects.filter(user=user).count() == 0

    response = auth_client.get("/api/v1/cart/")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ACTIVE"
    assert data["items"] == []

    assert Cart.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_get_cart_returns_existing_cart(auth_client, user):
    # prepare existing cart
    Cart.objects.create(user=user, status=Cart.Status.ACTIVE)

    response = auth_client.get("/api/v1/cart/")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ACTIVE"

    assert Cart.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_add_item_to_cart(auth_client, user):
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    auth_client.get("/api/v1/cart/")

    response = auth_client.post(
        "/api/v1/cart/items/",
        {
            "product_id": product.id,
            "quantity": 2,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["quantity"] == 2
