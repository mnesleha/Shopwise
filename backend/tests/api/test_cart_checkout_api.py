import pytest
from products.models import Product
from carts.models import Cart


@pytest.mark.django_db
def test_checkout_creates_order_with_items_and_total(auth_client, user):
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )

    response = auth_client.post("/api/v1/cart/checkout/")
    assert response.status_code == 201

    data = response.json()
    order = data["order"]

    assert order["status"] == "CREATED"
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 2
    assert order["total_price"] == "200.00"


@pytest.mark.django_db
def test_checkout_converts_cart_status(auth_client):
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    response = auth_client.post("/api/v1/cart/checkout/")
    assert response.status_code == 201

    cart = Cart.objects.get()
    assert cart.status == Cart.Status.CONVERTED


@pytest.mark.django_db
def test_new_cart_created_after_checkout(auth_client):
    auth_client.get("/api/v1/cart/")
    auth_client.post("/api/v1/cart/checkout/")
    response = auth_client.get("/api/v1/cart/")

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


@pytest.mark.django_db
def test_checkout_empty_cart_fails(auth_client):
    auth_client.get("/api/v1/cart/")
    response = auth_client.post("/api/v1/cart/checkout/")
    assert response.status_code == 400

    cart = Cart.objects.get()
    assert cart.status == Cart.Status.ACTIVE
