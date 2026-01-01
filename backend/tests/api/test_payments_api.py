import pytest
from orders.models import Order
from products.models import Product
from tests.conftest import create_order_via_checkout


@pytest.mark.django_db
def test_successful_payment_creates_payment_and_updates_order(auth_client, user):
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    # checkout
    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )

    checkout_response = auth_client.post("/api/v1/cart/checkout/").json()
    order_id = checkout_response["id"]

    response = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order_id, "result": "success"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "SUCCESS"


@pytest.mark.django_db
def test_failed_payment_marks_order_as_failed(auth_client, product):
    order = create_order_via_checkout(auth_client, product)

    response = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order["id"], "result": "fail"},
        format="json",
    )

    assert response.json()["status"] == "FAILED"


@pytest.mark.django_db
def test_payment_cannot_be_created_twice(auth_client, product):
    order = create_order_via_checkout(auth_client, product)

    auth_client.post(
        "/api/v1/payments/",
        {"order_id": order["id"], "result": "success"},
        format="json",
    )

    response = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order["id"], "result": "success"},
        format="json",
    )

    assert response.status_code == 409


@pytest.mark.django_db(transaction=True)
def test_payment_double_submit(auth_client, user, order_factory):
    order = order_factory(user=user)

    payload = {"order_id": order.id, "result": "success"}

    r1 = auth_client.post("/api/v1/payments/", payload, format="json")
    r2 = auth_client.post("/api/v1/payments/", payload, format="json")

    assert Order.objects.filter(id=order.id, user=user).exists()
    order_db = Order.objects.get(id=order.id)

    assert Order.objects.filter(id=order.id, user=user).exists()

    assert r1.status_code == 201
    assert r2.status_code == 409
