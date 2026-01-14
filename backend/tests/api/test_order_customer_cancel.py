import pytest

from orders.models import Order, InventoryReservation
from products.models import Product
from tests.conftest import checkout_payload


@pytest.mark.django_db
def test_customer_can_cancel_created_order(auth_client, user):
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    # add to cart
    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )

    # checkout -> CREATED order + ACTIVE reservation
    checkout_resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email),
        format="json",
    )
    assert checkout_resp.status_code == 201
    order_id = checkout_resp.json()["id"]

    # sanity check: reservation exists
    r = InventoryReservation.objects.get(order_id=order_id, product=product)
    assert r.status == InventoryReservation.Status.ACTIVE

    # cancel
    cancel_resp = auth_client.post(
        f"/api/v1/orders/{order_id}/cancel/",
        format="json",
    )
    assert cancel_resp.status_code == 200

    body = cancel_resp.json()

    # order state
    assert body["id"] == order_id
    assert body["status"] == Order.Status.CANCELLED
    assert body["cancel_reason"] == Order.CancelReason.CUSTOMER_REQUEST
    assert body["cancelled_by"] == Order.CancelledBy.CUSTOMER
    assert body["cancelled_at"] is not None

    # reservation released
    r.refresh_from_db()
    assert r.status == InventoryReservation.Status.RELEASED
    assert r.release_reason == InventoryReservation.ReleaseReason.CUSTOMER_REQUEST
    assert r.released_at is not None

    # physical stock unchanged (reserve did not decrement)
    product.refresh_from_db()
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_customer_cannot_cancel_paid_order(auth_client, user):
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
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    checkout_resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email),
        format="json",
    )
    order_id = checkout_resp.json()["id"]

    # payment success -> PAID
    pay_resp = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order_id, "result": "success"},
        format="json",
    )
    assert pay_resp.status_code == 201

    # attempt cancel
    cancel_resp = auth_client.post(
        f"/api/v1/orders/{order_id}/cancel/",
        format="json",
    )

    assert cancel_resp.status_code in (400, 409)
    body = cancel_resp.json()

    assert body["code"] == "INVALID_ORDER_STATE"


@pytest.mark.django_db
def test_customer_cancel_is_not_idempotent_and_fails_on_second_call(auth_client, user):
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
    checkout_resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email),
        format="json",
    )
    order_id = checkout_resp.json()["id"]

    # first cancel
    r1 = auth_client.post(f"/api/v1/orders/{order_id}/cancel/", format="json")
    assert r1.status_code == 200

    # second cancel -> invalid state
    r2 = auth_client.post(f"/api/v1/orders/{order_id}/cancel/", format="json")
    assert r2.status_code in (400, 409)
    assert r2.json()["code"] == "INVALID_ORDER_STATE"
