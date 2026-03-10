"""Tests for price_at_add_time gross semantics (Phase 3).

Verifies that CartItem.price_at_add_time always stores the customer-visible
gross unit price, not the legacy net price from product.price.

Test categories:
- Migrated product without tax: gross == net, so snapshot == price_net_amount.
- Migrated product with tax: snapshot must equal the tax-inclusive gross.
- Unmigrated product: fallback to product.price (no pricing pipeline).
- Snapshot via PATCH quantity upsert also stores gross.
"""
from decimal import Decimal

import pytest

from carts.models import Cart, CartItem
from products.models import Product, TaxClass
from tests.conftest import checkout_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _product_with_tax(*, name: str, price_net: Decimal, tax_rate: Decimal) -> Product:
    tc = TaxClass.objects.create(
        name=f"Tax {tax_rate}%",
        code=f"tax_{tax_rate}",
        rate=tax_rate,
        is_active=True,
    )
    return Product.objects.create(
        name=name,
        price=price_net,         # legacy field; intentionally mirrors net for clarity
        price_net_amount=price_net,
        currency="EUR",
        tax_class=tc,
        stock_quantity=10,
        is_active=True,
    )


def _product_no_tax(*, name: str, price_net: Decimal) -> Product:
    """Migrated product with no tax class (0 % effective rate)."""
    return Product.objects.create(
        name=name,
        price=price_net,
        price_net_amount=price_net,
        currency="EUR",
        stock_quantity=10,
        is_active=True,
    )


def _legacy_product(*, name: str, price: Decimal) -> Product:
    """Unmigrated product — no price_net_amount."""
    return Product.objects.create(
        name=name,
        price=price,
        stock_quantity=10,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Migrated product — no tax (gross == net)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_price_at_add_time_stores_gross_for_migrated_product_no_tax(auth_client):
    """Migrated product with no tax class: snapshot == net == gross."""
    product = _product_no_tax(name="No Tax", price_net=Decimal("80.00"))

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    cart = Cart.objects.filter(status=Cart.Status.ACTIVE).last()
    item = cart.items.get(product=product)

    # No tax → gross == net == 80.00
    assert item.price_at_add_time == Decimal("80.00")


# ---------------------------------------------------------------------------
# Migrated product — with tax class
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_price_at_add_time_stores_gross_for_migrated_product_with_tax(auth_client):
    """Migrated product with 23 % VAT: snapshot must be the tax-inclusive gross price.

    net 100.00 + 23 % tax = gross 123.00.
    The snapshot must be 123.00, NOT 100.00 (net).
    """
    product = _product_with_tax(name="Taxed", price_net=Decimal("100.00"), tax_rate=Decimal("23"))

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    cart = Cart.objects.filter(status=Cart.Status.ACTIVE).last()
    item = cart.items.get(product=product)

    # Gross = 100.00 × 1.23 = 123.00
    assert item.price_at_add_time == Decimal("123.00")


# ---------------------------------------------------------------------------
# Unmigrated product — fallback path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_price_at_add_time_fallback_for_unmigrated_product(auth_client):
    """Unmigrated products (no price_net_amount) fall back to product.price."""
    product = _legacy_product(name="Legacy", price=Decimal("49.99"))

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    cart = Cart.objects.filter(status=Cart.Status.ACTIVE).last()
    item = cart.items.get(product=product)

    assert item.price_at_add_time == Decimal("49.99")


# ---------------------------------------------------------------------------
# Snapshot via PATCH quantity (upsert create path)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_price_at_add_time_stores_gross_via_patch_upsert(auth_client):
    """PATCH /cart/items/<id>/ when item does not yet exist uses gross snapshot."""
    product = _product_with_tax(name="PATCH Taxed", price_net=Decimal("50.00"), tax_rate=Decimal("10"))
    # gross = 50.00 × 1.10 = 55.00

    auth_client.get("/api/v1/cart/")
    # Use PATCH with a new product — triggers the upsert-create path
    auth_client.patch(
        f"/api/v1/cart/items/{product.id}/",
        {"quantity": 2},
        format="json",
    )

    cart = Cart.objects.filter(status=Cart.Status.ACTIVE).last()
    item = cart.items.get(product=product)

    assert item.price_at_add_time == Decimal("55.00")


# ---------------------------------------------------------------------------
# No gross-vs-net comparison bug: preflight for taxed product returns NONE
# when price has not changed
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_false_positive_for_taxed_product_when_price_unchanged(auth_client):
    """For a taxed migrated product, price_at_add_time == current gross → NONE.

    Before this fix, price_at_add_time stored the NET price (product.price),
    while the comparison used the GROSS (pipeline output).  This caused a
    false-positive price-change detection even when the merchant did not change
    the price.  After the fix, both sides are gross → no spurious WARNING.
    """
    from django.test import override_settings

    with override_settings(
        CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
        CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
    ):
        product = _product_with_tax(name="Stable Taxed", price_net=Decimal("100.00"), tax_rate=Decimal("20"))
        # gross = 120.00

        auth_client.get("/api/v1/cart/")
        auth_client.post(
            "/api/v1/cart/items/",
            {"product_id": product.id, "quantity": 1},
            format="json",
        )

        # Price has NOT changed — preflight must return NONE, not WARNING.
        response = auth_client.get("/api/v1/cart/checkout/preflight/")
        assert response.status_code == 200
        data = response.json()
        pc = data["price_change"]

        assert pc["has_changes"] is False, (
            "price_at_add_time gross-vs-net bug: preflight incorrectly detected "
            "a price change on a product whose price did not change."
        )
        assert pc["severity"] == "NONE"
        assert pc["items"] == []
