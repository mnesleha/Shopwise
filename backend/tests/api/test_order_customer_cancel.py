import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from orders.models import Order, InventoryReservation
from products.models import Product
from tests.conftest import checkout_payload, create_valid_order


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

    assert cancel_resp.status_code == 409
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
    assert r2.status_code == 409
    assert r2.json()["code"] == "INVALID_ORDER_STATE"


@pytest.mark.django_db
def test_customer_cannot_cancel_order_of_another_user(auth_client, user):
    User = get_user_model()
    other_user = User.objects.create_user(
        email="other@example.com", password="Passw0rd!123")

    # other user's client
    other_client = auth_client
    other_client.force_authenticate(user=other_user)

    product = Product.objects.create(
        name="Product", price=100, stock_quantity=10, is_active=True)

    other_client.get("/api/v1/cart/")
    other_client.post("/api/v1/cart/items/",
                      {"product_id": product.id, "quantity": 1}, format="json")
    checkout_resp = other_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=other_user.email),
        format="json",
    )
    assert checkout_resp.status_code == 201
    order_id = checkout_resp.json()["id"]

    # switch back to original user
    auth_client.force_authenticate(user=user)

    cancel_resp = auth_client.post(
        f"/api/v1/orders/{order_id}/cancel/", format="json")
    assert cancel_resp.status_code == 404

    @pytest.mark.django_db
    def test_cancel_requires_authentication():
        client = APIClient()
        order = create_valid_order(
            user=None, status=Order.Status.CREATED, customer_email="g@example.com")

        resp = client.post(f"/api/v1/orders/{order.id}/cancel/", format="json")
        assert resp.status_code == 401
