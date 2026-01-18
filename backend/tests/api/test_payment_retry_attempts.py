import pytest

from orders.models import Order, InventoryReservation
from payments.models import Payment
from products.models import Product
from tests.conftest import create_order_via_checkout
pytestmark = pytest.mark.django_db


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
