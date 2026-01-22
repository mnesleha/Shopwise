import pytest
from django.db import transaction
from products.models import Product
from tests.e2e_mailpit.mailpit_client import MailpitClient


@pytest.mark.e2e_mailpit
@pytest.mark.django_db
def test_guest_order_link_email_is_delivered_to_mailpit(client, settings, monkeypatch):
    settings.PUBLIC_BASE_URL = "https://example.test"
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "127.0.0.1"
    settings.EMAIL_PORT = 1025
    settings.DEFAULT_FROM_EMAIL = "no-reply@shopwise.test"

    settings.Q_CLUSTER = {**getattr(settings, "Q_CLUSTER", {}), "sync": True}

    mailpit = MailpitClient("http://127.0.0.1:8025")
#    mailpit.purge()

    product = Product.objects.create(
        name="E2E_P1", price="10.00", stock_quantity=10, is_active=True)

    # 1) Create/resolve anonymous cart -> sets cart_token cookie
    resp = client.get("/api/v1/cart/")
    assert resp.status_code in (200, 201)
    assert "cart_token" in client.cookies, "Expected cart_token cookie to be set for anonymous cart"

    # 2) Add item to cart
    resp = client.post(
        "/api/v1/cart/items/",
        data={"product_id": product.id, "quantity": 1},
        content_type="application/json",
    )
    assert resp.status_code in (200, 201)

    payload = {
        "customer_email": "guest@example.com",
        "shipping_name": "John Doe",
        "shipping_address_line1": "123 Main St",
        "shipping_address_line2": "",
        "shipping_city": "Chicago",
        "shipping_postal_code": "60601",
        "shipping_country": "US",
        "shipping_phone": "+14155552671",
        "billing_same_as_shipping": True
    }

    # Capture on_commit callbacks so we can run them deterministically after checkout
    callbacks = []
    monkeypatch.setattr(transaction, "on_commit", lambda fn,
                        using=None: callbacks.append(fn))

    # 3) Checkout using the same client (cookie retained)
    resp = client.post("/api/v1/cart/checkout/", data=payload,
                       content_type="application/json")
    assert resp.status_code in (200, 201)

    assert len(
        callbacks) >= 1, "Expected at least one on_commit callback (enqueue email job)"
    for cb in callbacks:
        cb()  # simulate commit -> enqueue/execute sync Q2 job

    msg_meta = mailpit.wait_for_message_containing("guest@example.com")
    msg_id = msg_meta["ID"]
    msg = mailpit.get_message(msg_id)

    raw = str(msg)
    assert "guest@example.com" in raw
    assert "token=" in raw
    assert "https://example.test" in raw
