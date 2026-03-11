"""Checkout Slice 5 — snapshot persistence tests.

Verifies that, after a successful checkout, the new Phase 3 snapshot fields
are correctly persisted on both ``OrderItem`` and ``Order``.

Coverage
--------
- Non-promoted item: all Phase 3 OrderItem snapshot fields populated from
  the pricing pipeline (net, gross, tax, tax_rate; promo fields None).
- PERCENT-promoted item: promo snapshot fields captured; values match
  discounted pricing tier.
- FIXED-GROSS-promoted item: promo discount gross matches the fixed amount.
- Order totals: ``subtotal_gross``, ``subtotal_net``, ``total_tax``,
  ``total_discount``, ``currency`` all populated and arithmetically
  consistent.
- Mixed cart (promoted + non-promoted): aggregated order totals are the
  sum of the individual line snapshots.
- Unmigrated product (no ``price_net_amount``): Phase 3 snapshot fields are
  ``None``; legacy fields still filled in (backward compat).
- Guest checkout: Phase 3 fields populated in the same way.
"""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from categories.models import Category
from discounts.models import (
    Promotion,
    PromotionAmountScope,
    PromotionProduct,
    PromotionType,
)
from orderitems.models import OrderItem
from orders.models import Order
from products.models import Product, TaxClass
from tests.conftest import checkout_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tax_class(rate: Decimal, code: str = "std") -> TaxClass:
    return TaxClass.objects.create(name=code.title(), code=code, rate=rate)


def _product(
    *,
    name: str,
    price_net: Decimal,
    tax_class: TaxClass | None = None,
    category: Category | None = None,
    stock: int = 10,
) -> Product:
    """A fully-migrated product (``price_net_amount`` set)."""
    return Product.objects.create(
        name=name,
        price=price_net,
        stock_quantity=stock,
        is_active=True,
        price_net_amount=price_net,
        currency="EUR",
        tax_class=tax_class,
        category=category,
    )


def _unmigrated_product(*, name: str, price: Decimal, stock: int = 10) -> Product:
    """Legacy product without ``price_net_amount``."""
    return Product.objects.create(
        name=name,
        price=price,
        stock_quantity=stock,
        is_active=True,
        price_net_amount=None,
        currency="EUR",
    )


def _percent_promo(product: Product, *, code: str, value: Decimal) -> Promotion:
    promo = Promotion.objects.create(
        name=f"Promo {code}",
        code=code,
        type=PromotionType.PERCENT,
        value=value,
        priority=5,
        is_active=True,
    )
    PromotionProduct.objects.create(promotion=promo, product=product)
    return promo


def _fixed_gross_promo(product: Product, *, code: str, value: Decimal) -> Promotion:
    promo = Promotion.objects.create(
        name=f"Promo {code}",
        code=code,
        type=PromotionType.FIXED,
        value=value,
        priority=5,
        is_active=True,
        amount_scope=PromotionAmountScope.GROSS,
    )
    PromotionProduct.objects.create(promotion=promo, product=product)
    return promo


def _do_checkout(client, product: Product, quantity: int = 1):
    """Put product in cart and execute checkout; return (response, order)."""
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": quantity},
        format="json",
    )
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    assert response.status_code == 201, response.json()
    order = Order.objects.get(pk=response.json()["id"])
    return order


def _do_checkout_multi(client, products_and_qtys: list[tuple[Product, int]]):
    """Put multiple products in cart and execute checkout."""
    client.get("/api/v1/cart/")
    for product, qty in products_and_qtys:
        client.post(
            "/api/v1/cart/items/",
            {"product_id": product.id, "quantity": qty},
            format="json",
        )
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    assert response.status_code == 201, response.json()
    return Order.objects.get(pk=response.json()["id"])


# ---------------------------------------------------------------------------
# OrderItem snapshot — no-tax, non-promoted product
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_orderitem_snapshot_non_promoted_no_tax(auth_client):
    """Non-promoted product without a tax class: gross == net, tax == 0, promo fields None."""
    product = _product(name="No-Tax Widget", price_net=Decimal("50.00"))

    order = _do_checkout(auth_client, product)

    item = OrderItem.objects.get(order=order)
    assert item.unit_price_net_at_order_time == Decimal("50.00")
    assert item.unit_price_gross_at_order_time == Decimal("50.00")
    assert item.tax_amount_at_order_time == Decimal("0.00")
    assert item.tax_rate_at_order_time == Decimal("0.0000")
    assert item.promotion_code_at_order_time is None
    assert item.promotion_type_at_order_time is None
    assert item.promotion_discount_gross_at_order_time is None


@pytest.mark.django_db
def test_orderitem_snapshot_non_promoted_with_tax(auth_client):
    """Non-promoted product with 10 % VAT: tax snapshot reflects the tax class."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10")
    product = _product(name="Taxed Widget", price_net=Decimal("100.00"), tax_class=tc)

    order = _do_checkout(auth_client, product)

    item = OrderItem.objects.get(order=order)
    assert item.unit_price_net_at_order_time == Decimal("100.00")
    assert item.unit_price_gross_at_order_time == Decimal("110.00")
    assert item.tax_amount_at_order_time == Decimal("10.00")
    assert item.tax_rate_at_order_time == Decimal("10.0000")  # percentage, not fraction
    assert item.promotion_code_at_order_time is None
    assert item.promotion_type_at_order_time is None


# ---------------------------------------------------------------------------
# OrderItem snapshot — PERCENT-promoted product
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_orderitem_snapshot_percent_promotion(auth_client):
    """PERCENT promotion: snapshot fields reflect discounted net/gross/tax."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10p")
    product = _product(name="Percent Promo Widget", price_net=Decimal("100.00"), tax_class=tc)
    _percent_promo(product, code="pct10", value=Decimal("10.00"))

    # With 10 % net discount and 10 % VAT:
    # discounted net = 90.00, discounted gross = 99.00, tax = 9.00
    order = _do_checkout(auth_client, product)

    item = OrderItem.objects.get(order=order)
    assert item.unit_price_net_at_order_time == Decimal("90.00")
    assert item.unit_price_gross_at_order_time == Decimal("99.00")
    assert item.tax_amount_at_order_time == Decimal("9.00")
    assert item.tax_rate_at_order_time == Decimal("10.0000")  # percentage, not fraction
    assert item.promotion_code_at_order_time == "pct10"
    assert item.promotion_type_at_order_time == "PERCENT"
    # Discount gross = undiscounted_gross - discounted_gross = 110 - 99 = 11
    assert item.promotion_discount_gross_at_order_time == Decimal("11.00")


@pytest.mark.django_db
def test_orderitem_snapshot_percent_promotion_no_tax(auth_client):
    """PERCENT promo on zero-tax product: promo_discount_gross == net discount amount."""
    product = _product(name="No-Tax Promo Widget", price_net=Decimal("100.00"))
    _percent_promo(product, code="pct20", value=Decimal("20.00"))

    # discounted net == gross = 80.00; tax = 0
    order = _do_checkout(auth_client, product)

    item = OrderItem.objects.get(order=order)
    assert item.unit_price_net_at_order_time == Decimal("80.00")
    assert item.unit_price_gross_at_order_time == Decimal("80.00")
    assert item.tax_amount_at_order_time == Decimal("0.00")
    assert item.promotion_code_at_order_time == "pct20"
    assert item.promotion_type_at_order_time == "PERCENT"
    assert item.promotion_discount_gross_at_order_time == Decimal("20.00")


# ---------------------------------------------------------------------------
# OrderItem snapshot — FIXED-GROSS-promoted product
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_orderitem_snapshot_fixed_gross_promotion(auth_client):
    """FIXED GROSS promotion: promo_discount_gross equals the fixed amount."""
    product = _product(name="Fixed Promo Widget", price_net=Decimal("80.00"))
    _fixed_gross_promo(product, code="minus15", value=Decimal("15.00"))

    # No tax class: net == gross = 80 - 15 = 65
    order = _do_checkout(auth_client, product)

    item = OrderItem.objects.get(order=order)
    assert item.unit_price_gross_at_order_time == Decimal("65.00")
    assert item.unit_price_net_at_order_time == Decimal("65.00")
    assert item.tax_amount_at_order_time == Decimal("0.00")
    assert item.promotion_code_at_order_time == "minus15"
    assert item.promotion_type_at_order_time == "FIXED"
    assert item.promotion_discount_gross_at_order_time == Decimal("15.00")


# ---------------------------------------------------------------------------
# OrderItem snapshot — multi-unit quantity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_orderitem_snapshot_multi_unit_quantity(auth_client):
    """Snapshot unit fields are per-unit (not multiplied by quantity)."""
    product = _product(name="Multi Widget", price_net=Decimal("25.00"))

    order = _do_checkout(auth_client, product, quantity=4)

    item = OrderItem.objects.get(order=order)
    assert item.unit_price_net_at_order_time == Decimal("25.00")
    assert item.unit_price_gross_at_order_time == Decimal("25.00")
    # Legacy line total should be quantity * unit_gross
    assert item.line_total_at_order_time == Decimal("100.00")


# ---------------------------------------------------------------------------
# Order totals snapshot — single item
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_totals_snapshot_single_item_no_tax(auth_client):
    """Order totals reflect a single non-promoted, no-tax item."""
    product = _product(name="Totals Widget", price_net=Decimal("49.99"))

    order = _do_checkout(auth_client, product, quantity=2)

    order.refresh_from_db()
    assert order.currency == "EUR"
    assert order.subtotal_gross == Decimal("99.98")
    assert order.subtotal_net == Decimal("99.98")
    assert order.total_tax == Decimal("0.00")
    assert order.total_discount == Decimal("0.00")


@pytest.mark.django_db
def test_order_totals_snapshot_single_item_with_tax(auth_client):
    """Order totals include tax when tax class is set."""
    tc = _tax_class(rate=Decimal("20.0000"), code="vat20")
    product = _product(name="Taxed Totals Widget", price_net=Decimal("100.00"), tax_class=tc)

    order = _do_checkout(auth_client, product)

    order.refresh_from_db()
    assert order.currency == "EUR"
    assert order.subtotal_gross == Decimal("120.00")
    assert order.total_tax == Decimal("20.00")
    assert order.subtotal_net == Decimal("100.00")
    assert order.total_discount == Decimal("0.00")


@pytest.mark.django_db
def test_order_totals_snapshot_with_promotion(auth_client):
    """total_discount reflects the gross discount; totals reflect discounted price."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10d")
    product = _product(name="Promoted Totals Widget", price_net=Decimal("100.00"), tax_class=tc)
    _percent_promo(product, code="pct10tot", value=Decimal("10.00"))

    # undiscounted gross = 110, discounted gross = 99, discount = 11
    order = _do_checkout(auth_client, product)

    order.refresh_from_db()
    assert order.subtotal_gross == Decimal("99.00")
    assert order.subtotal_net == Decimal("90.00")
    assert order.total_tax == Decimal("9.00")
    assert order.total_discount == Decimal("11.00")


# ---------------------------------------------------------------------------
# Order totals snapshot — mixed cart (arithmetic consistency)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_totals_snapshot_mixed_cart(auth_client):
    """Mixed cart: order totals equal the sum of individual line snapshots."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10m")
    p1 = _product(name="Widget A", price_net=Decimal("40.00"), tax_class=tc)
    p2 = _product(name="Widget B", price_net=Decimal("60.00"))
    _percent_promo(p1, code="mixed-pct10", value=Decimal("10.00"))

    # p1: discounted net=36, gross=39.60, tax=3.60, discount gross=4.40
    # p2: net=gross=60.00, tax=0.00, discount=0.00
    # totals: subtotal_gross=99.60, subtotal_net=96.00, total_tax=3.60, total_discount=4.40
    order = _do_checkout_multi(auth_client, [(p1, 1), (p2, 1)])

    order.refresh_from_db()
    items = {oi.product_id: oi for oi in OrderItem.objects.filter(order=order)}

    # Line-level consistency
    item_a = items[p1.id]
    assert item_a.unit_price_net_at_order_time == Decimal("36.00")
    assert item_a.unit_price_gross_at_order_time == Decimal("39.60")
    assert item_a.tax_amount_at_order_time == Decimal("3.60")

    item_b = items[p2.id]
    assert item_b.unit_price_net_at_order_time == Decimal("60.00")
    assert item_b.unit_price_gross_at_order_time == Decimal("60.00")
    assert item_b.tax_amount_at_order_time == Decimal("0.00")

    # Order-level totals
    assert order.subtotal_gross == Decimal("99.60")
    assert order.total_tax == Decimal("3.60")
    assert order.subtotal_net == Decimal("96.00")
    assert order.total_discount == Decimal("4.40")
    assert order.currency == "EUR"

    # Arithmetic: subtotal_net == subtotal_gross - total_tax
    assert order.subtotal_net == order.subtotal_gross - order.total_tax


# ---------------------------------------------------------------------------
# Unmigrated product — Phase 3 fields are None, legacy fields intact
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_orderitem_snapshot_unmigrated_product_new_fields_are_none(auth_client):
    """Unmigrated product: Phase 3 fields are None; legacy snapshot still filled."""
    product = _unmigrated_product(name="Legacy Widget", price=Decimal("30.00"))

    client = auth_client
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    assert response.status_code == 201
    order = Order.objects.get(pk=response.json()["id"])

    item = OrderItem.objects.get(order=order)
    # Phase 3 fields — must be None for unmigrated products
    assert item.unit_price_net_at_order_time is None
    assert item.unit_price_gross_at_order_time is None
    assert item.tax_amount_at_order_time is None
    assert item.tax_rate_at_order_time is None
    assert item.promotion_code_at_order_time is None
    assert item.promotion_type_at_order_time is None
    assert item.promotion_discount_gross_at_order_time is None
    # Legacy fields — must still be populated
    assert item.unit_price_at_order_time == Decimal("30.00")
    assert item.line_total_at_order_time == Decimal("30.00")
    assert item.price_at_order_time == Decimal("30.00")


# ---------------------------------------------------------------------------
# Guest checkout — Phase 3 fields populated
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_guest_checkout_snapshot_fields_populated():
    """Guest (unauthenticated) checkout populates the Phase 3 snapshot fields."""
    product = _product(name="Guest Widget", price_net=Decimal("29.99"))
    _percent_promo(product, code="guest-pct5", value=Decimal("5.00"))

    # discounted net = gross = 28.49 (5 % off 29.99, no tax)
    client = APIClient()
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    assert response.status_code == 201
    order = Order.objects.get(pk=response.json()["id"])

    item = OrderItem.objects.get(order=order)
    assert item.unit_price_net_at_order_time is not None
    assert item.unit_price_gross_at_order_time is not None
    assert item.promotion_code_at_order_time == "guest-pct5"
    assert item.promotion_type_at_order_time == "PERCENT"

    order.refresh_from_db()
    assert order.currency == "EUR"
    assert order.subtotal_gross is not None
    assert order.total_discount is not None


# ---------------------------------------------------------------------------
# Legacy fields still populated for backward compat (serializer reads them)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_legacy_snapshot_fields_still_populated_alongside_phase3(auth_client):
    """Legacy snapshot fields remain populated when Phase 3 fields are also written."""
    product = _product(name="Dual Snapshot Widget", price_net=Decimal("100.00"))

    order = _do_checkout(auth_client, product)

    item = OrderItem.objects.get(order=order)
    # Phase 3
    assert item.unit_price_net_at_order_time == Decimal("100.00")
    assert item.unit_price_gross_at_order_time == Decimal("100.00")
    # Legacy — must still be present
    assert item.unit_price_at_order_time == Decimal("100.00")
    assert item.line_total_at_order_time == Decimal("100.00")
    assert item.price_at_order_time == Decimal("100.00")
