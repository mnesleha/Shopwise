from unittest.mock import patch
import pytest
from django.db import transaction
from rest_framework.test import APIRequestFactory

from api.views.carts import CartCheckoutView
from carts.models import Cart, CartItem
from products.models import Product


pytestmark = pytest.mark.django_db


def _capture_on_commit(monkeypatch):
    callbacks = []

    def fake_on_commit(fn, using=None):
        callbacks.append(fn)

    monkeypatch.setattr(transaction, "on_commit", fake_on_commit)
    return callbacks


def test_anonymous_checkout_enqueues_guest_order_link_email(monkeypatch, settings):
    settings.PUBLIC_BASE_URL = "https://example.test"

    # --- Arrange minimal sellable product ---
    product = Product.objects.create(
        name="E2E_TEST_PRODUCT",
        price="10.00",
        stock_quantity=10,
        is_active=True,
    )

    # --- Arrange an anonymous ACTIVE cart with one item ---
    cart = Cart.objects.create(
        user=None, status=Cart.Status.ACTIVE, anonymous_token_hash="x" * 64)
    CartItem.objects.create(cart=cart, product=product,
                            quantity=1, price_at_add_time=product.price)

    # --- Prepare request payload expected by CartCheckoutRequestSerializer ---
    payload = {
        "customer_email": "guest@example.com",
        "shipping_name": "Guest User",
        "shipping_address_line1": "Somewhere 1",
        "shipping_city": "City",
        "shipping_postal_code": "12345",
        "shipping_country": "US",
        "shipping_phone": "+1 555 000",
        "billing_same_as_shipping": True,
    }

    callbacks = _capture_on_commit(monkeypatch)

    rf = APIRequestFactory()
    request = rf.post("/api/v1/cart/checkout/", payload, format="json")

    # Make the request anonymous explicitly
    request.user = type("Anon", (), {"is_authenticated": False})()

    # Ensure the checkout resolves the cart (we pass token through header/cookie in real flow).
    # This depends on your cart resolver; if you need X-Cart-Token, add it here accordingly.
    request.META["HTTP_X_CART_TOKEN"] = "raw-token-does-not-matter-here"

    # Patch guest token issuance and url generation to be deterministic
    with patch("api.views.carts._get_active_cart_for_request", return_value=cart):
        with patch("api.views.carts.GuestOrderAccessService.issue_token", return_value="guest_tok_456"):
            with patch("api.views.carts.generate_guest_access_url", return_value="https://example.test/orders/1?token=guest_tok_456"):
                with patch("api.views.carts.async_task") as async_task_mock:
                    resp = CartCheckoutView.as_view()(request)

                    assert resp.status_code == 201
                    assert len(callbacks) == 1

                    callbacks[0]()  # simulate commit

                    assert async_task_mock.call_count == 1

    args, kwargs = async_task_mock.call_args
    assert args[0] == "notifications.jobs.send_guest_order_link"
    assert kwargs["recipient_email"] == "guest@example.com"
    assert "order_number" in kwargs
    assert kwargs["guest_order_url"].endswith("token=guest_tok_456")
