"""Phase 3 Slice 5 — order detail invoice snapshot API tests.

Verifies that:
- product_name_at_order_time is persisted at checkout
- line_total_net_at_order_time and line_total_gross_at_order_time are persisted
- Order detail API response includes all Phase 3 Slice 5 snapshot fields
- product_name in API response uses the snapshot value, not the live product name
- vat_breakdown payload is correct for single-rate and zero-rate orders
- vat_breakdown groups correctly for multi-rate orders
- created_at is present in the API response
- subtotal_net / subtotal_gross / total_tax / currency are present in the response
- Legacy response fields (unit_price, line_total) remain intact
"""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from discounts.models import (
    AcquisitionMode,
    OrderPromotion,
    Promotion,
    PromotionProduct,
    PromotionType,
    StackingPolicy,
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
    stock: int = 10,
) -> Product:
    return Product.objects.create(
        name=name,
        price=price_net,
        stock_quantity=stock,
        is_active=True,
        price_net_amount=price_net,
        currency="EUR",
        tax_class=tax_class,
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


def _do_checkout(client, product: Product, quantity: int = 1) -> Order:
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": quantity},
        format="json",
    )
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    assert response.status_code == 201, response.json()
    return Order.objects.get(pk=response.json()["id"])


def _get_order_detail(client, order: Order) -> dict:
    response = client.get(f"/api/v1/orders/{order.id}/")
    assert response.status_code == 200, response.json()
    return response.json()


# ---------------------------------------------------------------------------
# Product name snapshot — model level
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_product_name_at_order_time_stored(auth_client):
    """product_name_at_order_time is populated from product.name at checkout."""
    product = _product(name="Premium Headphones", price_net=Decimal("80.00"))
    order = _do_checkout(auth_client, product)

    item = OrderItem.objects.get(order=order)
    assert item.product_name_at_order_time == "Premium Headphones"


@pytest.mark.django_db
def test_product_name_snapshot_is_stable_after_product_rename(auth_client):
    """Changing the product name after checkout does not affect the snapshot."""
    product = _product(name="Original Name", price_net=Decimal("50.00"))
    order = _do_checkout(auth_client, product)

    # Rename the product after the order was placed
    product.name = "Changed Name"
    product.save()

    item = OrderItem.objects.get(order=order)
    assert item.product_name_at_order_time == "Original Name"


# ---------------------------------------------------------------------------
# Line total snapshot — model level
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_line_total_net_stored_for_migrated_product(auth_client):
    """line_total_net_at_order_time is populated (unit_net × qty) for migrated products."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10lt")
    product = _product(name="Taxed Widget", price_net=Decimal("100.00"), tax_class=tc)

    order = _do_checkout(auth_client, product, quantity=2)

    item = OrderItem.objects.get(order=order)
    # net per unit = 100.00, × 2 = 200.00
    assert item.line_total_net_at_order_time == Decimal("200.00")


@pytest.mark.django_db
def test_line_total_gross_stored_for_migrated_product(auth_client):
    """line_total_gross_at_order_time is populated (unit_gross × qty) for migrated products."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10ltg")
    product = _product(name="Taxed Widget G", price_net=Decimal("100.00"), tax_class=tc)

    order = _do_checkout(auth_client, product, quantity=3)

    item = OrderItem.objects.get(order=order)
    # gross per unit = 110.00, × 3 = 330.00
    assert item.line_total_gross_at_order_time == Decimal("330.00")


@pytest.mark.django_db
def test_line_total_net_equals_unit_net_times_qty(auth_client):
    """line_total_net = unit_price_net × quantity exactly."""
    product = _product(name="Simple Widget", price_net=Decimal("25.00"))

    order = _do_checkout(auth_client, product, quantity=4)

    item = OrderItem.objects.get(order=order)
    assert item.line_total_net_at_order_time == item.unit_price_net_at_order_time * 4


# ---------------------------------------------------------------------------
# Order detail API — snapshot field presence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_api_response_includes_product_name(auth_client):
    """Order detail API includes product_name from snapshot."""
    product = _product(name="API Test Widget", price_net=Decimal("60.00"))
    order = _do_checkout(auth_client, product)

    data = _get_order_detail(auth_client, order)
    item = data["items"][0]
    assert item["product_name"] == "API Test Widget"


@pytest.mark.django_db
def test_api_product_name_uses_snapshot_not_live_name(auth_client):
    """API response uses product_name_at_order_time even if live product name changed."""
    product = _product(name="Snapshot Name", price_net=Decimal("60.00"))
    order = _do_checkout(auth_client, product)

    product.name = "Updated Live Name"
    product.save()

    data = _get_order_detail(auth_client, order)
    assert data["items"][0]["product_name"] == "Snapshot Name"


@pytest.mark.django_db
def test_api_response_includes_unit_price_net_and_gross(auth_client):
    """Order detail API includes unit_price_net and unit_price_gross."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10api")
    product = _product(name="Taxed API Widget", price_net=Decimal("100.00"), tax_class=tc)
    order = _do_checkout(auth_client, product)

    data = _get_order_detail(auth_client, order)
    item = data["items"][0]
    assert item["unit_price_net"] == "100.00"
    assert item["unit_price_gross"] == "110.00"


@pytest.mark.django_db
def test_api_response_includes_tax_amount_and_tax_rate(auth_client):
    """Order detail API includes tax_amount and tax_rate snapshot fields."""
    tc = _tax_class(rate=Decimal("20.0000"), code="vat20api")
    product = _product(name="Tax Rate Widget", price_net=Decimal("100.00"), tax_class=tc)
    order = _do_checkout(auth_client, product)

    data = _get_order_detail(auth_client, order)
    item = data["items"][0]
    assert item["tax_amount"] == "20.00"
    assert item["tax_rate"] == "20.00"


@pytest.mark.django_db
def test_api_response_includes_line_total_net_and_gross(auth_client):
    """Order detail API includes line_total_net and line_total_gross."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10ltapi")
    product = _product(name="Line Total Widget", price_net=Decimal("100.00"), tax_class=tc)
    order = _do_checkout(auth_client, product, quantity=2)

    data = _get_order_detail(auth_client, order)
    item = data["items"][0]
    assert item["line_total_net"] == "200.00"
    assert item["line_total_gross"] == "220.00"


@pytest.mark.django_db
def test_api_response_includes_created_at(auth_client):
    """Order detail API includes created_at as an ISO timestamp."""
    product = _product(name="Timestamp Widget", price_net=Decimal("10.00"))
    order = _do_checkout(auth_client, product)

    data = _get_order_detail(auth_client, order)
    assert data["created_at"] is not None
    assert "T" in data["created_at"]  # ISO 8601 format


@pytest.mark.django_db
def test_api_response_includes_order_level_totals(auth_client):
    """Order detail API includes subtotal_net, subtotal_gross, total_tax, currency."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10ord")
    product = _product(name="Order Totals Widget", price_net=Decimal("100.00"), tax_class=tc)
    order = _do_checkout(auth_client, product)

    data = _get_order_detail(auth_client, order)
    assert data["subtotal_net"] == "100.00"
    assert data["subtotal_gross"] == "110.00"
    assert data["total_tax"] == "10.00"
    assert data["currency"] == "EUR"


@pytest.mark.django_db
def test_legacy_unit_price_and_line_total_still_present(auth_client):
    """Backward-compat: legacy unit_price and line_total fields remain in the response."""
    product = _product(name="Legacy Compat Widget", price_net=Decimal("50.00"))
    order = _do_checkout(auth_client, product, quantity=2)

    data = _get_order_detail(auth_client, order)
    item = data["items"][0]
    assert item["unit_price"] == "50.00"
    assert item["line_total"] == "100.00"


# ---------------------------------------------------------------------------
# VAT breakdown payload
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_vat_breakdown_zero_rate(auth_client):
    """VAT breakdown for a zero-tax item: vat_amount = 0, tax_base = total_incl_vat."""
    product = _product(name="Zero Tax Widget", price_net=Decimal("50.00"))
    order = _do_checkout(auth_client, product, quantity=2)

    data = _get_order_detail(auth_client, order)
    breakdown = data["vat_breakdown"]
    assert len(breakdown) == 1
    row = breakdown[0]
    assert row["tax_rate"] == "0.00"
    assert row["tax_base"] == "100.00"
    assert row["vat_amount"] == "0.00"
    assert row["total_incl_vat"] == "100.00"


@pytest.mark.django_db
def test_vat_breakdown_with_tax(auth_client):
    """VAT breakdown correctly separates net and tax for a taxed item."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10vb")
    product = _product(name="Taxed Breakdown Widget", price_net=Decimal("100.00"), tax_class=tc)
    order = _do_checkout(auth_client, product, quantity=2)

    data = _get_order_detail(auth_client, order)
    breakdown = data["vat_breakdown"]
    assert len(breakdown) == 1
    row = breakdown[0]
    assert row["tax_rate"] == "10.00"
    assert row["tax_base"] == "200.00"        # 2 × 100.00 net
    assert row["vat_amount"] == "20.00"       # 2 × 10.00 tax
    assert row["total_incl_vat"] == "220.00"  # 2 × 110.00 gross


@pytest.mark.django_db
def test_vat_breakdown_promoted_item_uses_discounted_values(auth_client):
    """VAT breakdown uses discounted (post-promotion) line totals."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10promo")
    product = _product(name="Promo VAT Widget", price_net=Decimal("100.00"), tax_class=tc)
    _percent_promo(product, code="vat10promo-pct10", value=Decimal("10.00"))

    # discounted net=90, gross=99, tax=9
    order = _do_checkout(auth_client, product)

    data = _get_order_detail(auth_client, order)
    row = data["vat_breakdown"][0]
    assert row["tax_rate"] == "10.00"
    assert row["tax_base"] == "90.00"
    assert row["vat_amount"] == "9.00"
    assert row["total_incl_vat"] == "99.00"


@pytest.mark.django_db
def test_vat_breakdown_multi_rate(auth_client):
    """VAT breakdown groups items by tax rate; each group has separate totals."""
    tc_10 = _tax_class(rate=Decimal("10.0000"), code="vat10mr")
    tc_20 = _tax_class(rate=Decimal("20.0000"), code="vat20mr")

    client = auth_client
    client.get("/api/v1/cart/")
    p1 = _product(name="10pct Product", price_net=Decimal("100.00"), tax_class=tc_10)
    p2 = _product(name="20pct Product", price_net=Decimal("50.00"), tax_class=tc_20)

    client.post("/api/v1/cart/items/", {"product_id": p1.id, "quantity": 1}, format="json")
    client.post("/api/v1/cart/items/", {"product_id": p2.id, "quantity": 1}, format="json")
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    assert response.status_code == 201
    order = Order.objects.get(pk=response.json()["id"])

    data = _get_order_detail(auth_client, order)
    breakdown = data["vat_breakdown"]
    assert len(breakdown) == 2

    by_rate = {row["tax_rate"]: row for row in breakdown}

    row_10 = by_rate["10.00"]
    assert row_10["tax_base"] == "100.00"
    assert row_10["vat_amount"] == "10.00"
    assert row_10["total_incl_vat"] == "110.00"

    row_20 = by_rate["20.00"]
    assert row_20["tax_base"] == "50.00"
    assert row_20["vat_amount"] == "10.00"
    assert row_20["total_incl_vat"] == "60.00"


@pytest.mark.django_db
def test_vat_breakdown_sorted_ascending_by_rate(auth_client):
    """VAT breakdown rows are sorted in ascending order by tax rate."""
    tc_20 = _tax_class(rate=Decimal("20.0000"), code="vat20sort")
    tc_5 = _tax_class(rate=Decimal("5.0000"), code="vat5sort")

    client = auth_client
    client.get("/api/v1/cart/")
    p1 = _product(name="20 pct Widget", price_net=Decimal("50.00"), tax_class=tc_20)
    p2 = _product(name="5 pct Widget", price_net=Decimal("40.00"), tax_class=tc_5)

    client.post("/api/v1/cart/items/", {"product_id": p1.id, "quantity": 1}, format="json")
    client.post("/api/v1/cart/items/", {"product_id": p2.id, "quantity": 1}, format="json")
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    assert response.status_code == 201
    order = Order.objects.get(pk=response.json()["id"])

    data = _get_order_detail(auth_client, order)
    rates = [row["tax_rate"] for row in data["vat_breakdown"]]
    from decimal import Decimal as D
    assert rates == sorted(rates, key=lambda r: D(r))


# ---------------------------------------------------------------------------
# Phase 4 — explicit pre/post order-discount payload fields
# ---------------------------------------------------------------------------


def _order_promotion(*, code: str, value: Decimal, minimum_order_value: Decimal | None = None) -> OrderPromotion:
    """Create an AUTO_APPLY PERCENT order-level promotion."""
    return OrderPromotion.objects.create(
        name=f"Promo {code}",
        code=code,
        type=PromotionType.PERCENT,
        value=value,
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=10,
        is_active=True,
        minimum_order_value=minimum_order_value,
    )


def _do_checkout_with_order_promo(
    client,
    product: Product,
    quantity: int = 1,
    *,
    promo_value: Decimal = Decimal("10"),
    min_order_value: Decimal | None = None,
) -> Order:
    """Add product to cart, create an auto-apply order promotion, and checkout."""
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": quantity},
        format="json",
    )
    _order_promotion(
        code=f"PROMO-{product.id}-{promo_value}",
        value=promo_value,
        minimum_order_value=min_order_value,
    )
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    assert response.status_code == 201, response.json()
    return Order.objects.get(pk=response.json()["id"])


# ---- order_discount_gross is present ----


@pytest.mark.django_db
def test_order_discount_gross_present_in_response(auth_client):
    """order_discount_gross is returned in the order detail response when OD was applied."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10od1")
    product = _product(name="OD Product 1", price_net=Decimal("100.00"), tax_class=tc)

    # gross = 110.00; 10 % OD → order_discount_gross = 11.00
    order = _do_checkout_with_order_promo(auth_client, product, promo_value=Decimal("10"))

    data = _get_order_detail(auth_client, order)
    assert data["order_discount_gross"] == "11.00"


@pytest.mark.django_db
def test_order_discount_gross_null_when_no_order_promotion(auth_client):
    """order_discount_gross is null when no order-level discount was applied."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10od2")
    product = _product(name="OD Product 2", price_net=Decimal("100.00"), tax_class=tc)
    order = _do_checkout(auth_client, product)

    data = _get_order_detail(auth_client, order)
    assert data["order_discount_gross"] is None


# ---- pre_order_discount_subtotal_gross ----


@pytest.mark.django_db
def test_pre_order_discount_subtotal_gross_correct(auth_client):
    """pre_order_discount_subtotal_gross equals the sum of item gross line totals before OD."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10pod1")
    product = _product(name="POD Product 1", price_net=Decimal("100.00"), tax_class=tc)

    # gross = 110.00; 10 % OD → net = subtotal_gross + OD = 99.00 + 11.00 = 110.00
    order = _do_checkout_with_order_promo(auth_client, product, promo_value=Decimal("10"))

    data = _get_order_detail(auth_client, order)
    assert data["pre_order_discount_subtotal_gross"] == "110.00"


@pytest.mark.django_db
def test_pre_order_discount_subtotal_gross_equals_total_when_no_od(auth_client):
    """When no OD exists, pre_order_discount_subtotal_gross equals the final gross total."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10pod2")
    product = _product(name="POD Product 2", price_net=Decimal("100.00"), tax_class=tc)
    order = _do_checkout(auth_client, product)

    data = _get_order_detail(auth_client, order)
    # No OD: pre-discount subtotal == final total == subtotal_gross
    assert data["pre_order_discount_subtotal_gross"] == data["total"]
    assert data["pre_order_discount_subtotal_gross"] == "110.00"


# ---- post_order_discount_* fields ----


@pytest.mark.django_db
def test_post_order_discount_fields_correct(auth_client):
    """post_order_discount_total_gross / _subtotal_net / _total_tax are arithmetically correct."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10post1")
    product = _product(name="POST Product 1", price_net=Decimal("100.00"), tax_class=tc)

    # gross = 110.00; 10 % OD = 11.00
    # adjusted_gross = 99.00, adjusted_net = 90.00, adjusted_tax = 9.00
    order = _do_checkout_with_order_promo(auth_client, product, promo_value=Decimal("10"))

    data = _get_order_detail(auth_client, order)

    assert data["post_order_discount_total_gross"] == "99.00"
    assert data["post_order_discount_subtotal_net"] == "90.00"
    assert data["post_order_discount_total_tax"] == "9.00"

    # arithmetic invariant: net + tax == gross
    net = Decimal(data["post_order_discount_subtotal_net"])
    tax = Decimal(data["post_order_discount_total_tax"])
    gross = Decimal(data["post_order_discount_total_gross"])
    assert net + tax == gross


@pytest.mark.django_db
def test_post_order_discount_total_gross_matches_total(auth_client):
    """post_order_discount_total_gross must equal the top-level total field."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10post2")
    product = _product(name="POST Product 2", price_net=Decimal("100.00"), tax_class=tc)
    order = _do_checkout_with_order_promo(auth_client, product, promo_value=Decimal("10"))

    data = _get_order_detail(auth_client, order)
    assert data["post_order_discount_total_gross"] == data["total"]


# ---- VAT breakdown: post-OD allocation truth ----


@pytest.mark.django_db
def test_vat_breakdown_reflects_post_order_discount_allocation(auth_client):
    """VAT breakdown total_incl_vat equals post-OD total_gross when OD is applied."""
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10vbd1")
    product = _product(name="VBD Product 1", price_net=Decimal("100.00"), tax_class=tc)

    # 10 % OD; gross=110, adjusted=99
    order = _do_checkout_with_order_promo(auth_client, product, promo_value=Decimal("10"))

    data = _get_order_detail(auth_client, order)
    vb = data["vat_breakdown"]
    assert len(vb) == 1
    row = vb[0]

    assert row["tax_rate"] == "10.00"
    assert row["tax_base"] == "90.00"
    assert row["vat_amount"] == "9.00"
    assert row["total_incl_vat"] == "99.00"

    # breakdown total must equal final order total
    assert row["total_incl_vat"] == data["total"]


@pytest.mark.django_db
def test_vat_breakdown_sum_equals_post_od_total_for_multi_rate(auth_client):
    """Sum of VAT breakdown total_incl_vat equals post-OD total when multiple VAT rates exist."""
    tc_10 = _tax_class(rate=Decimal("10.0000"), code="vat10vbd2")
    tc_21 = _tax_class(rate=Decimal("21.0000"), code="vat21vbd2")

    client = auth_client
    client.get("/api/v1/cart/")
    p1 = _product(name="10pct VBD Product", price_net=Decimal("100.00"), tax_class=tc_10)
    p2 = _product(name="21pct VBD Product", price_net=Decimal("50.00"), tax_class=tc_21)

    client.post("/api/v1/cart/items/", {"product_id": p1.id, "quantity": 1}, format="json")
    client.post("/api/v1/cart/items/", {"product_id": p2.id, "quantity": 1}, format="json")

    # gross_p1 = 110.00, gross_p2 = 60.50 → total_gross = 170.50
    # 10 % OD = 17.05; post-OD = 153.45
    _order_promotion(code="OD-MULTI-VBD", value=Decimal("10"))

    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    assert response.status_code == 201
    order = Order.objects.get(pk=response.json()["id"])

    data = _get_order_detail(auth_client, order)
    breakdown_sum = sum(Decimal(row["total_incl_vat"]) for row in data["vat_breakdown"])
    assert breakdown_sum == Decimal(data["total"])


# ---- Payload consistency ----


@pytest.mark.django_db
def test_payload_is_internally_consistent_with_order_discount(auth_client):
    """All order-level fields are self-consistent when OD is applied.

    Invariants checked:
    - pre_order_discount_subtotal_gross - order_discount_gross == post_order_discount_total_gross
    - post_order_discount_subtotal_net + post_order_discount_total_tax == post_order_discount_total_gross
    - total == post_order_discount_total_gross
    - VAT breakdown sum == total
    """
    tc = _tax_class(rate=Decimal("10.0000"), code="vat10cons")
    product = _product(name="Consistency Product", price_net=Decimal("100.00"), tax_class=tc)

    order = _do_checkout_with_order_promo(auth_client, product, promo_value=Decimal("10"))
    data = _get_order_detail(auth_client, order)

    pre_gross = Decimal(data["pre_order_discount_subtotal_gross"])
    od_gross = Decimal(data["order_discount_gross"])
    post_gross = Decimal(data["post_order_discount_total_gross"])
    post_net = Decimal(data["post_order_discount_subtotal_net"])
    post_tax = Decimal(data["post_order_discount_total_tax"])
    total = Decimal(data["total"])

    assert pre_gross - od_gross == post_gross, (
        f"pre({pre_gross}) - OD({od_gross}) should equal post({post_gross})"
    )
    assert post_net + post_tax == post_gross, (
        f"net({post_net}) + tax({post_tax}) should equal gross({post_gross})"
    )
    assert total == post_gross, f"total({total}) should equal post_gross({post_gross})"

    vb_total = sum(Decimal(row["total_incl_vat"]) for row in data["vat_breakdown"])
    assert vb_total == total, f"VAT breakdown sum({vb_total}) should equal total({total})"
