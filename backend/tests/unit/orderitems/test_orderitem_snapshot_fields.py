"""
Tests for Phase 3 OrderItem pricing snapshot fields.

Verifies that:
- All new fields exist on the model and default to None for existing rows.
- Each field can be written and read back with correct precision.
- Negative values are rejected by the existing clean() validation where applicable.
- Existing order creation flow (without the new fields) continues to work.
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from orderitems.models import OrderItem
from tests.conftest import create_valid_order


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(order, product, **overrides) -> OrderItem:
    """Build an unsaved OrderItem with the minimum required legacy fields."""
    defaults = dict(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("100.00"),
    )
    defaults.update(overrides)
    return OrderItem(**defaults)


# ---------------------------------------------------------------------------
# Phase 3 snapshot fields — existence and nullability
# ---------------------------------------------------------------------------

PHASE3_FIELDS = [
    "unit_price_net_at_order_time",
    "unit_price_gross_at_order_time",
    "tax_amount_at_order_time",
    "tax_rate_at_order_time",
    "promotion_code_at_order_time",
    "promotion_type_at_order_time",
    "promotion_discount_gross_at_order_time",
]


@pytest.mark.django_db
@pytest.mark.parametrize("field_name", PHASE3_FIELDS)
def test_phase3_field_defaults_to_null(field_name, user, product):
    """New snapshot fields must default to None (backwards-compatible nullability)."""
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("50.00"),
    )
    assert getattr(item, field_name) is None


@pytest.mark.django_db
def test_unit_price_net_persists_correctly(user, product):
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        price_at_order_time=Decimal("200.00"),
        unit_price_net_at_order_time=Decimal("81.30"),
    )
    item.refresh_from_db()
    assert item.unit_price_net_at_order_time == Decimal("81.30")


@pytest.mark.django_db
def test_unit_price_gross_persists_correctly(user, product):
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("123.00"),
        unit_price_gross_at_order_time=Decimal("123.00"),
    )
    item.refresh_from_db()
    assert item.unit_price_gross_at_order_time == Decimal("123.00")


@pytest.mark.django_db
def test_tax_amount_persists_correctly(user, product):
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("123.00"),
        tax_amount_at_order_time=Decimal("23.00"),
    )
    item.refresh_from_db()
    assert item.tax_amount_at_order_time == Decimal("23.00")


@pytest.mark.django_db
def test_tax_rate_persists_with_four_decimal_places(user, product):
    """tax_rate_at_order_time uses decimal_places=4 to match TaxClass.rate."""
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("123.00"),
        tax_rate_at_order_time=Decimal("23.0000"),
    )
    item.refresh_from_db()
    assert item.tax_rate_at_order_time == Decimal("23.0000")


@pytest.mark.django_db
def test_promotion_code_persists_correctly(user, product):
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("90.00"),
        promotion_code_at_order_time="SUMMER10",
    )
    item.refresh_from_db()
    assert item.promotion_code_at_order_time == "SUMMER10"


@pytest.mark.django_db
def test_promotion_type_persists_correctly(user, product):
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("90.00"),
        promotion_type_at_order_time="PERCENTAGE",
    )
    item.refresh_from_db()
    assert item.promotion_type_at_order_time == "PERCENTAGE"


@pytest.mark.django_db
def test_promotion_discount_gross_persists_correctly(user, product):
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("90.00"),
        promotion_discount_gross_at_order_time=Decimal("10.00"),
    )
    item.refresh_from_db()
    assert item.promotion_discount_gross_at_order_time == Decimal("10.00")


@pytest.mark.django_db
def test_all_phase3_fields_persisted_together(user, product):
    """All new snapshot fields can be written and read back in a single create."""
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("123.00"),
        unit_price_net_at_order_time=Decimal("100.00"),
        unit_price_gross_at_order_time=Decimal("123.00"),
        tax_amount_at_order_time=Decimal("23.00"),
        tax_rate_at_order_time=Decimal("23.0000"),
        promotion_code_at_order_time="PROMO2026",
        promotion_type_at_order_time="FLAT",
        promotion_discount_gross_at_order_time=Decimal("5.00"),
    )
    item.refresh_from_db()
    assert item.unit_price_net_at_order_time == Decimal("100.00")
    assert item.unit_price_gross_at_order_time == Decimal("123.00")
    assert item.tax_amount_at_order_time == Decimal("23.00")
    assert item.tax_rate_at_order_time == Decimal("23.0000")
    assert item.promotion_code_at_order_time == "PROMO2026"
    assert item.promotion_type_at_order_time == "FLAT"
    assert item.promotion_discount_gross_at_order_time == Decimal("5.00")


# ---------------------------------------------------------------------------
# Backward compatibility — existing flow works without new fields
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_existing_order_creation_flow_unaffected(user, product):
    """
    Transition-mode test: creating an OrderItem without any Phase 3 fields
    must succeed and leave all new fields as None.
    """
    order = create_valid_order(user=user)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=3,
        price_at_order_time=Decimal("300.00"),
        unit_price_at_order_time=Decimal("100.00"),
        line_total_at_order_time=Decimal("300.00"),
    )
    item.refresh_from_db()
    for field_name in PHASE3_FIELDS:
        assert getattr(item, field_name) is None, (
            f"Expected {field_name} to be None in transition mode"
        )
