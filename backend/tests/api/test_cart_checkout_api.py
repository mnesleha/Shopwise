import re
from decimal import Decimal
import pytest
from unittest.mock import patch
from products.models import Product
from carts.models import Cart
from orders.models import Order
from orderitems.models import OrderItem


def assert_checkout_contract(order: dict) -> None:
    """
    Contract guard for POST /api/v1/cart/checkout/ response.

    We intentionally keep this strict to prevent accidental schema drift
    (e.g. leaking extra Order/OrderItem fields via implicit ModelSerializer output).
    """
    assert isinstance(order, dict)

    # top-level shape
    assert set(order.keys()) == {"id", "status", "items", "total"}

    assert isinstance(order["id"], int)
    assert order["id"] > 0

    assert isinstance(order["status"], str)
    assert order["status"]  # non-empty

    assert isinstance(order["items"], list)
    assert len(order["items"]) >= 1

    # items shape
    item = order["items"][0]
    assert isinstance(item, dict)
    assert set(item.keys()) == {"id", "product",
                                "quantity", "unit_price", "line_total", "discount"}

    assert isinstance(item["id"], int)
    assert isinstance(item["product"], int)
    assert isinstance(item["quantity"], int)
    assert item["quantity"] > 0

    assert isinstance(item["unit_price"], str)
    assert re.match(r"^\d+\.\d{2}$", item["unit_price"])

    assert isinstance(item["line_total"], str)
    assert re.match(r"^\d+\.\d{2}$", item["line_total"])

    if item["discount"] is not None:
        assert set(item["discount"].keys()) == {"type", "value"}
        assert item["discount"]["type"] in {"FIXED", "PERCENT"}
        assert re.match(r"^\d+\.\d{2}$", item["discount"]["value"])
    else:
        assert item["discount"] is None

    # total format
    assert isinstance(order["total"], str)
    assert re.match(r"^\d+\.\d{2}$", order["total"])


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

    order = response.json()

    # CONTRACT GUARD (this is what will make RED now)
    assert_checkout_contract(order)

    # business expectations
    assert order["status"] == "CREATED"
    assert len(order["items"]) == 1
    assert order["items"][0]["product"] == product.id
    assert order["items"][0]["quantity"] == 2
    assert order["total"] == "200.00"


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


@pytest.mark.django_db
def test_double_checkout_returns_409(auth_client):
    product = Product.objects.create(
        name="Test Product",
        price=Decimal("100.00"),
        stock_quantity=10,
        is_active=True,
    )

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    # First checkout – OK
    first = auth_client.post("/api/v1/cart/checkout/")
    assert first.status_code == 201

    # Second checkout – MUST FAIL
    second = auth_client.post("/api/v1/cart/checkout/")
    assert second.status_code == 409
    assert second.json()["message"] == "Cart has already been checked out."

    # Still only ONE order
    assert Order.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_checkout_rolls_back_on_order_item_failure(auth_client, user):
    product = Product.objects.create(
        name="Rollback Product",
        price=Decimal("100.00"),
        stock_quantity=10,
        is_active=True,
    )

    # create cart + item
    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    cart = Cart.objects.get(user=user, status=Cart.Status.ACTIVE)

    # sanity check before checkout
    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0
    assert cart.status == Cart.Status.ACTIVE

    # force failure INSIDE transaction
    with patch(
        "api.views.carts.OrderItem.objects.create",
        side_effect=Exception("Boom during order item creation"),
    ):
        response = auth_client.post("/api/v1/cart/checkout/")

    # response can be 500 or mapped error – not the focus here
    assert response.status_code >= 400

    # ASSERT ROLLBACK
    cart.refresh_from_db()
    assert cart.status == Cart.Status.ACTIVE

    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0
