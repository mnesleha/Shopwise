import pytest

from orders.models import Order, InventoryReservation
from payments.models import Payment
from products.models import Product
from tests.conftest import create_order_via_checkout
pytestmark = pytest.mark.django_db


def test_payment_retry_creates_new_attempt_and_succeeds(auth_client, user):
    product = Product.objects.create(
        name="Product", price=100, stock_quantity=10, is_active=True)

    # Reuse the same helper you already use in other tests
    # adjust if needed
    order_data = create_order_via_checkout(
        auth_client, product, customer_email=user.email)
    order_id = order_data["id"]

    # First attempt fails
    r1 = auth_client.post(
        "/api/v1/payments/", {"order_id": order_id, "result": "fail"}, format="json")
    assert r1.status_code == 201
    order = Order.objects.get(id=order_id)
    assert order.status == Order.Status.PAYMENT_FAILED
    assert Payment.objects.filter(order_id=order_id).count() == 1
    assert Payment.objects.filter(
        order_id=order_id, status=Payment.Status.FAILED).count() == 1

    # Reservations still ACTIVE
    res = InventoryReservation.objects.get(
        order_id=order_id, product_id=product.id)
    assert res.status == InventoryReservation.Status.ACTIVE

    # Second attempt succeeds (new Payment row)
    r2 = auth_client.post(
        "/api/v1/payments/", {"order_id": order_id, "result": "success"}, format="json")
    assert r2.status_code == 201
    order.refresh_from_db()
    assert order.status == Order.Status.PAID

    assert Payment.objects.filter(order_id=order_id).count() == 2
    assert Payment.objects.filter(
        order_id=order_id, status=Payment.Status.SUCCESS).count() == 1


def test_payment_retry_blocked_if_success_payment_exists(auth_client, user):
    product = Product.objects.create(
        name="Product", price=100, stock_quantity=10, is_active=True)

    # adjust if needed
    order_data = create_order_via_checkout(
        auth_client, product, customer_email=user.email)
    order_id = order_data["id"]

    r1 = auth_client.post(
        "/api/v1/payments/", {"order_id": order_id, "result": "success"}, format="json")
    assert r1.status_code == 201
    assert Payment.objects.filter(
        order_id=order_id, status=Payment.Status.SUCCESS).count() == 1

    # Second attempt must be blocked
    r2 = auth_client.post(
        "/api/v1/payments/", {"order_id": order_id, "result": "success"}, format="json")
    assert r2.status_code == 409
    assert r2.json()["code"] == "PAYMENT_ALREADY_EXISTS"
