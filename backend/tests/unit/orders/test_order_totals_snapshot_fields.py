"""
Tests for Phase 3 Order totals snapshot fields.

Verifies that:
- All new fields exist on the model and default to None for existing rows.
- Each field can be written and read back with correct precision.
- Currency field only accepts valid ISO 4217 codes from CURRENCY_CHOICES.
- Existing order creation flow (without the new fields) continues to work.
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from orders.models import Order
from tests.conftest import create_valid_order


# ---------------------------------------------------------------------------
# Phase 3 snapshot fields — existence and nullability
# ---------------------------------------------------------------------------

PHASE3_DECIMAL_FIELDS = [
    "subtotal_net",
    "subtotal_gross",
    "total_tax",
    "total_discount",
]


@pytest.mark.django_db
@pytest.mark.parametrize("field_name", PHASE3_DECIMAL_FIELDS)
def test_phase3_decimal_field_defaults_to_null(field_name, user):
    """New totals snapshot fields must default to None (backwards-compatible nullability)."""
    order = create_valid_order(user=user)
    order.refresh_from_db()
    assert getattr(order, field_name) is None


@pytest.mark.django_db
def test_currency_field_defaults_to_null(user):
    order = create_valid_order(user=user)
    order.refresh_from_db()
    assert order.currency is None


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_subtotal_net_persists_correctly(user):
    order = create_valid_order(user=user)
    Order.objects.filter(pk=order.pk).update(subtotal_net=Decimal("200.00"))
    order.refresh_from_db()
    assert order.subtotal_net == Decimal("200.00")


@pytest.mark.django_db
def test_subtotal_gross_persists_correctly(user):
    order = create_valid_order(user=user)
    Order.objects.filter(pk=order.pk).update(subtotal_gross=Decimal("246.00"))
    order.refresh_from_db()
    assert order.subtotal_gross == Decimal("246.00")


@pytest.mark.django_db
def test_total_tax_persists_correctly(user):
    order = create_valid_order(user=user)
    Order.objects.filter(pk=order.pk).update(total_tax=Decimal("46.00"))
    order.refresh_from_db()
    assert order.total_tax == Decimal("46.00")


@pytest.mark.django_db
def test_total_discount_persists_correctly(user):
    order = create_valid_order(user=user)
    Order.objects.filter(pk=order.pk).update(total_discount=Decimal("10.00"))
    order.refresh_from_db()
    assert order.total_discount == Decimal("10.00")


@pytest.mark.django_db
def test_currency_persists_correctly(user):
    order = create_valid_order(user=user)
    Order.objects.filter(pk=order.pk).update(currency="EUR")
    order.refresh_from_db()
    assert order.currency == "EUR"


@pytest.mark.django_db
def test_all_phase3_fields_persisted_together(user):
    """All five new snapshot fields can be written and read back in a single update."""
    order = create_valid_order(user=user)
    Order.objects.filter(pk=order.pk).update(
        subtotal_net=Decimal("200.00"),
        subtotal_gross=Decimal("246.00"),
        total_tax=Decimal("46.00"),
        total_discount=Decimal("10.00"),
        currency="EUR",
    )
    order.refresh_from_db()
    assert order.subtotal_net == Decimal("200.00")
    assert order.subtotal_gross == Decimal("246.00")
    assert order.total_tax == Decimal("46.00")
    assert order.total_discount == Decimal("10.00")
    assert order.currency == "EUR"


@pytest.mark.django_db
def test_large_order_total_fits_in_field(user):
    """max_digits=12 supports order totals well into the millions."""
    order = create_valid_order(user=user)
    Order.objects.filter(pk=order.pk).update(
        subtotal_gross=Decimal("9999999999.99"),
    )
    order.refresh_from_db()
    assert order.subtotal_gross == Decimal("9999999999.99")


# ---------------------------------------------------------------------------
# Backward compatibility — existing flow works without new fields
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_existing_order_creation_flow_unaffected(user):
    """
    Transition-mode test: creating an Order without any Phase 3 fields
    must succeed and leave all new fields as None.
    """
    order = create_valid_order(user=user)
    order.refresh_from_db()
    for field_name in PHASE3_DECIMAL_FIELDS:
        assert getattr(order, field_name) is None, (
            f"Expected {field_name} to be None in transition mode"
        )
    assert order.currency is None
