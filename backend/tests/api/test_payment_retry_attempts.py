import pytest

from orders.models import Order, InventoryReservation
from orders.services.inventory_reservation_service import reserve_for_checkout
from payments.models import Payment
from products.models import Product
from tests.conftest import create_order_via_checkout, create_valid_order
pytestmark = pytest.mark.django_db


def test_payment_retry_blocked_if_success_payment_exists(auth_client, user):
    product = Product.objects.create(
        name="Product", price=100, stock_quantity=10, is_active=True)

    # Checkout now auto-pays (COD); order has a SUCCESS payment immediately.
    order_data = create_order_via_checkout(
        auth_client, product, customer_email=user.email)
    order_id = order_data["id"]

    # A SUCCESS payment was already created during checkout.
    assert Payment.objects.filter(
        order_id=order_id, status=Payment.Status.SUCCESS).count() == 1

    # Any further manual payment attempt must be blocked with 409.
    r = auth_client.post(
        "/api/v1/payments/", {"order_id": order_id, "result": "success"}, format="json")
    assert r.status_code == 409
    assert r.json()["code"] == "PAYMENT_ALREADY_EXISTS"
