"""Checkout price-change detection — API integration tests.

Tests the price_change key in the POST /api/v1/cart/checkout/ response.
All tests use migrated products (price_net_amount set) unless explicitly
testing the unmigrated fallback.

The info/warning thresholds are overridden in each test that needs a
specific classification, keeping tests independent of the global defaults.
"""
from decimal import Decimal

import pytest
from django.test import override_settings

from products.models import Product
from discounts.models import (
    Promotion,
    PromotionAmountScope,
    PromotionProduct,
    PromotionType,
)
from tests.conftest import checkout_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _product(
    *,
    name: str,
    price_net: Decimal,
    stock: int = 10,
) -> Product:
    return Product.objects.create(
        name=name,
        price=price_net,
        stock_quantity=stock,
        is_active=True,
        price_net_amount=price_net,
        currency="EUR",
    )


def _add_to_cart(client, product: Product, quantity: int = 1):
    client.get("/api/v1/cart/")
    return client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": quantity},
        format="json",
    )


def _checkout(client):
    return client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")


# ---------------------------------------------------------------------------
# price_change key is always present in a successful checkout response
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_checkout_response_includes_price_change_key(auth_client):
    """The price_change key is always present in a 201 checkout response."""
    product = _product(name="Stable", price_net=Decimal("50.00"))
    _add_to_cart(auth_client, product)

    response = _checkout(auth_client)
    assert response.status_code == 201
    data = response.json()
    assert "price_change" in data
    pc = data["price_change"]
    assert "has_changes" in pc
    assert "severity" in pc
    assert "affected_items" in pc
    assert "items" in pc


# ---------------------------------------------------------------------------
# No price change → NONE
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_no_price_change_returns_none_severity(auth_client):
    """When price_net_amount does not change between add and checkout, has_changes=False."""
    product = _product(name="Unchanged", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    response = _checkout(auth_client)
    data = response.json()
    pc = data["price_change"]

    assert pc["has_changes"] is False
    assert pc["severity"] == "NONE"
    assert pc["affected_items"] == 0
    assert pc["items"] == []


# ---------------------------------------------------------------------------
# Small change below threshold → NONE
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_small_change_below_info_threshold_is_none(auth_client):
    """A 0.5 % price change is below the 1 % INFO threshold → NONE."""
    product = _product(name="Tiny Change", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    # Raise price by 0.50 (0.5 %)
    product.price = Decimal("100.50")
    product.price_net_amount = Decimal("100.50")
    product.save()

    response = _checkout(auth_client)
    data = response.json()
    pc = data["price_change"]

    assert pc["has_changes"] is False
    assert pc["severity"] == "NONE"


# ---------------------------------------------------------------------------
# Change above INFO threshold but below WARNING → INFO
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_change_above_info_below_warning_is_info(auth_client):
    """A 3 % price increase (1 % ≤ x < 5 %) → severity INFO."""
    product = _product(name="Moderate Increase", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    product.price = Decimal("103.00")
    product.price_net_amount = Decimal("103.00")
    product.save()

    response = _checkout(auth_client)
    data = response.json()
    pc = data["price_change"]

    assert pc["has_changes"] is True
    assert pc["severity"] == "INFO"
    assert pc["affected_items"] == 1
    assert len(pc["items"]) == 1
    item = pc["items"][0]
    assert item["direction"] == "UP"
    assert item["severity"] == "INFO"
    assert item["old_unit_gross"] == "100.00"
    assert item["new_unit_gross"] == "103.00"


# ---------------------------------------------------------------------------
# Change at/above WARNING threshold → WARNING
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_change_at_warning_threshold_is_warning(auth_client):
    """A 5 % price increase (x ≥ 5 %) → severity WARNING."""
    product = _product(name="Big Increase", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    product.price = Decimal("105.00")
    product.price_net_amount = Decimal("105.00")
    product.save()

    response = _checkout(auth_client)
    data = response.json()
    pc = data["price_change"]

    assert pc["has_changes"] is True
    assert pc["severity"] == "WARNING"
    item = pc["items"][0]
    assert item["severity"] == "WARNING"
    assert item["percent_change"] == "5.00"


# ---------------------------------------------------------------------------
# Price decrease is classified correctly
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_price_decrease_above_threshold_is_classified_correctly(auth_client):
    """A 10 % price decrease → direction=DOWN, severity=WARNING."""
    product = _product(name="Sale Item", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    product.price = Decimal("90.00")
    product.price_net_amount = Decimal("90.00")
    product.save()

    response = _checkout(auth_client)
    data = response.json()
    pc = data["price_change"]

    assert pc["has_changes"] is True
    assert pc["severity"] == "WARNING"
    item = pc["items"][0]
    assert item["direction"] == "DOWN"
    assert item["absolute_change"] == "-10.00"
    assert item["percent_change"] == "10.00"


# ---------------------------------------------------------------------------
# Cart-level summary aggregation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_cart_level_summary_reflects_highest_severity(auth_client):
    """Cart-level severity is the highest severity across all changed lines."""
    product_a = _product(name="Info Change", price_net=Decimal("100.00"))
    product_b = _product(name="Warning Change", price_net=Decimal("200.00"))

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product_a.id, "quantity": 1},
        format="json",
    )
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product_b.id, "quantity": 1},
        format="json",
    )

    # product_a: +2% → INFO; product_b: +10% → WARNING
    product_a.price = Decimal("102.00")
    product_a.price_net_amount = Decimal("102.00")
    product_a.save()

    product_b.price = Decimal("220.00")
    product_b.price_net_amount = Decimal("220.00")
    product_b.save()

    response = _checkout(auth_client)
    data = response.json()
    pc = data["price_change"]

    assert pc["severity"] == "WARNING"
    assert pc["affected_items"] == 2
    assert len(pc["items"]) == 2


# ---------------------------------------------------------------------------
# Unmigrated product fallback remains safe
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unmigrated_product_price_change_is_not_reported(auth_client):
    """Unmigrated products (price_net_amount=None) never generate price_change items."""
    product = Product.objects.create(
        name="Legacy Product",
        price=Decimal("50.00"),
        stock_quantity=10,
        is_active=True,
        # price_net_amount intentionally omitted
    )
    _add_to_cart(auth_client, product)

    # Mutate legacy price — should not appear in price_change
    product.price = Decimal("75.00")
    product.save()

    response = _checkout(auth_client)
    assert response.status_code == 201
    data = response.json()

    pc = data["price_change"]
    assert pc["has_changes"] is False
    assert pc["affected_items"] == 0
    assert pc["items"] == []


# ---------------------------------------------------------------------------
# Product with active promotion — price_change compares against discount-aware gross
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_promotion_applied_price_change_compares_gross(auth_client):
    """When a promotion is active, price_change compares price_at_add_time
    (snapshot at add time, before promotion was applied) against the current
    discounted gross from the pipeline.

    Product added at price_net=100 (gross=100, no tax, no promo at add time).
    Merchant adds a 20 % promotion afterwards.
    At checkout: current gross = 80.
    price_at_add_time = 100 → 20 % decrease → WARNING.
    """
    product = _product(name="Later Promo", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product)

    # Merchant adds a 20 % OFF promotion after the customer added to cart.
    promo = Promotion.objects.create(
        name="20 pct flash sale",
        code="flash-20pct",
        type=PromotionType.PERCENT,
        value=Decimal("20.00"),
        is_active=True,
    )
    PromotionProduct.objects.create(promotion=promo, product=product)

    response = _checkout(auth_client)
    data = response.json()
    pc = data["price_change"]

    # The customer sees a lower price at checkout than when they added it.
    assert pc["has_changes"] is True
    assert pc["severity"] == "WARNING"
    item = pc["items"][0]
    assert item["direction"] == "DOWN"
    assert item["old_unit_gross"] == "100.00"
    assert item["new_unit_gross"] == "80.00"
