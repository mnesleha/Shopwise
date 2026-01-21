from unittest.mock import patch

import pytest
from django.db import transaction

from rest_framework.test import APIRequestFactory

from api.views.carts import CartCheckoutView
from carts.models import Cart, CartItem
from products.models import Product

pytestmark = pytest.mark.django_db


def _capture_on_commit_callback(monkeypatch):
    callbacks = []

    def fake_on_commit(func, using=None):
        callbacks.append(func)

    monkeypatch.setattr(transaction, "on_commit", fake_on_commit)
    return callbacks


def test_guest_checkout_enqueues_guest_order_email_on_commit(monkeypatch, client, settings):
    """
    This test asserts wiring behavior for guest checkout:
    - guest checkout issues token + URL
    - transaction.on_commit schedules Q2 job: notifications.jobs.send_guest_order_link
    """
    callbacks = _capture_on_commit_callback(monkeypatch)
    settings.PUBLIC_BASE_URL = "https://example.test"

    product = Product.objects.create(
        name="E2E_TEST_PRODUCT",
        price="10.00",
        stock_quantity=10,
        is_active=True,
    )
    cart = Cart.objects.create(
        user=None, status=Cart.Status.ACTIVE, anonymous_token_hash="x" * 64)
    CartItem.objects.create(cart=cart, product=product,
                            quantity=1, price_at_add_time=product.price)

    payload = {
        "customer_email": "guest@example.com",
        "shipping_name": "E2E Customer",
        "shipping_address_line1": "E2E Main Street 1",
        "shipping_address_line2": "",
        "shipping_city": "E2E City",
        "shipping_postal_code": "00000",
        "shipping_country": "US",
        "shipping_phone": "+10000000000",
        "billing_same_as_shipping": True,
    }

    rf = APIRequestFactory()
    request = rf.post("/api/v1/cart/checkout/", payload, format="json")
    request.user = type("Anon", (), {"is_authenticated": False})()

    with patch("api.views.carts._get_active_cart_for_request", return_value=cart):
        with patch("api.views.carts.async_task") as async_task_mock:
            resp = CartCheckoutView.as_view()(request)

            assert resp.status_code == 201
            assert len(callbacks) == 1
            callbacks[0]()
            assert async_task_mock.call_count == 1

    assert len(callbacks) == 1

    callbacks[0]()

    assert async_task_mock.call_count == 1
    args, kwargs = async_task_mock.call_args
    assert args[0] == "notifications.jobs.send_guest_order_link"
    assert kwargs["recipient_email"] == "guest@example.com"
    assert "order_number" in kwargs
    assert "guest_order_url" in kwargs
    assert "https://example.test" in kwargs["guest_order_url"]
    assert "token=" in kwargs["guest_order_url"]
