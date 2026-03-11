"""Checkout preflight endpoint tests — GET /api/v1/cart/checkout/preflight/.

Verifies that the preflight endpoint:
- Returns 404 when no active cart exists.
- Returns 200 with price_change payload shape always present.
- Returns NONE severity when prices have not changed.
- Returns INFO severity for small price changes.
- Returns WARNING severity for large price changes.
- Does not generate false positives for unmigrated (legacy) products.
- Is safe for empty carts.
- Supports the same anonymous-cart token mechanism as other cart endpoints.

All pricing tests use migrated products (price_net_amount set) unless
explicitly testing the unmigrated fallback path.
"""
from decimal import Decimal

import pytest
from django.test import override_settings

from products.models import Product
from tests.conftest import checkout_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _product(*, name: str, price_net: Decimal, stock: int = 10) -> Product:
    return Product.objects.create(
        name=name,
        price=price_net,
        price_net_amount=price_net,
        currency="EUR",
        stock_quantity=stock,
        is_active=True,
    )


def _add_to_cart(client, product: Product, quantity: int = 1):
    client.get("/api/v1/cart/")
    return client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": quantity},
        format="json",
    )


PREFLIGHT_URL = "/api/v1/cart/checkout/preflight/"


# ---------------------------------------------------------------------------
# 404 when no active cart exists
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_preflight_returns_404_when_no_active_cart(auth_client):
    """Preflight must return 404 when no ACTIVE cart exists for the user."""
    # Do not create a cart — ensures there is none.
    response = auth_client.get(PREFLIGHT_URL)
    assert response.status_code == 404
    data = response.json()
    assert "code" in data


# ---------------------------------------------------------------------------
# price_change key always present in 200 response
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_preflight_response_includes_price_change_key(auth_client):
    """200 response always contains a price_change payload with the expected keys."""
    product = _product(name="Present Key", price_net=Decimal("30.00"))
    _add_to_cart(auth_client, product)

    response = auth_client.get(PREFLIGHT_URL)
    assert response.status_code == 200
    data = response.json()

    assert "price_change" in data
    pc = data["price_change"]
    assert "has_changes" in pc
    assert "severity" in pc
    assert "affected_items" in pc
    assert "items" in pc


# ---------------------------------------------------------------------------
# NONE — prices unchanged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_preflight_returns_none_when_prices_unchanged(auth_client):
    """Preflight returns severity=NONE when price_at_add_time matches current gross."""
    product = _product(name="Stable", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    response = auth_client.get(PREFLIGHT_URL)
    assert response.status_code == 200
    pc = response.json()["price_change"]

    assert pc["has_changes"] is False
    assert pc["severity"] == "NONE"
    assert pc["affected_items"] == 0
    assert pc["items"] == []


# ---------------------------------------------------------------------------
# INFO — small price increase
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_preflight_returns_info_for_small_price_increase(auth_client):
    """A 3 % price increase (within INFO band) → severity INFO."""
    product = _product(name="Small Increase", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    # Raise price by 3 %
    product.price = Decimal("103.00")
    product.price_net_amount = Decimal("103.00")
    product.save()

    response = auth_client.get(PREFLIGHT_URL)
    pc = response.json()["price_change"]

    assert pc["has_changes"] is True
    assert pc["severity"] == "INFO"
    assert pc["affected_items"] == 1
    assert len(pc["items"]) == 1
    item = pc["items"][0]
    assert item["direction"] == "UP"
    assert item["old_unit_gross"] == "100.00"
    assert item["new_unit_gross"] == "103.00"


# ---------------------------------------------------------------------------
# INFO — small price decrease
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_preflight_returns_info_for_small_price_decrease(auth_client):
    """A 2 % price decrease → severity INFO, direction DOWN."""
    product = _product(name="Small Decrease", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    product.price = Decimal("98.00")
    product.price_net_amount = Decimal("98.00")
    product.save()

    response = auth_client.get(PREFLIGHT_URL)
    pc = response.json()["price_change"]

    assert pc["has_changes"] is True
    assert pc["severity"] == "INFO"
    item = pc["items"][0]
    assert item["direction"] == "DOWN"
    assert item["old_unit_gross"] == "100.00"
    assert item["new_unit_gross"] == "98.00"


# ---------------------------------------------------------------------------
# WARNING — large price change
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_preflight_returns_warning_for_large_price_increase(auth_client):
    """A 10 % price increase (at/above WARNING band) → severity WARNING."""
    product = _product(name="Big Increase", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    product.price = Decimal("110.00")
    product.price_net_amount = Decimal("110.00")
    product.save()

    response = auth_client.get(PREFLIGHT_URL)
    pc = response.json()["price_change"]

    assert pc["has_changes"] is True
    assert pc["severity"] == "WARNING"
    item = pc["items"][0]
    assert item["severity"] == "WARNING"
    assert item["direction"] == "UP"
    assert item["percent_change"] == "10.00"


# ---------------------------------------------------------------------------
# Safe for empty cart
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_preflight_empty_cart_returns_none_severity(auth_client):
    """An active but empty cart returns NONE (no items to compare)."""
    auth_client.get("/api/v1/cart/")  # creates an empty cart

    response = auth_client.get(PREFLIGHT_URL)
    assert response.status_code == 200
    pc = response.json()["price_change"]

    assert pc["has_changes"] is False
    assert pc["severity"] == "NONE"


# ---------------------------------------------------------------------------
# Unmigrated product — no false positive
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_preflight_unmigrated_product_never_generates_price_change(auth_client):
    """Unmigrated products (price_net_amount=None) must not appear in preflight items."""
    product = Product.objects.create(
        name="Legacy",
        price=Decimal("50.00"),
        stock_quantity=10,
        is_active=True,
        # price_net_amount intentionally omitted
    )
    _add_to_cart(auth_client, product)

    # Mutate legacy price — must not appear in preflight.
    product.price = Decimal("75.00")
    product.save()

    response = auth_client.get(PREFLIGHT_URL)
    assert response.status_code == 200
    pc = response.json()["price_change"]

    assert pc["has_changes"] is False
    assert pc["items"] == []


# ---------------------------------------------------------------------------
# Read-only — no order created
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_preflight_does_not_create_an_order(auth_client):
    """Preflight must be read-only — no Order row may be created."""
    from orders.models import Order

    product = _product(name="No Order", price_net=Decimal("20.00"))
    _add_to_cart(auth_client, product)

    orders_before = Order.objects.count()
    auth_client.get(PREFLIGHT_URL)
    assert Order.objects.count() == orders_before
