"""Unit tests for carts.services.price_change.

These tests are pure Python — no database, no Django test runner needed
(though pytest-django is still used for settings access via @override_settings).

The cart_pricing argument to detect_price_changes is constructed from
SimpleNamespace stubs so tests remain fast and isolated from the ORM.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.test import override_settings

from carts.services.price_change import (
    CartPriceChangeSummary,
    PriceChangeDirection,
    PriceChangeSeverity,
    detect_price_changes,
    serialize_price_change_summary,
)


# ---------------------------------------------------------------------------
# Helpers — minimal stub factories
# ---------------------------------------------------------------------------


def _gross(amount: str):
    """Return a SimpleNamespace mimicking prices.Money.amount."""
    return SimpleNamespace(amount=Decimal(amount))


def _discounted(gross_amount: str):
    return SimpleNamespace(gross=_gross(gross_amount))


def _unit_pricing(discounted_gross: str):
    """Migrated product unit pricing stub."""
    return SimpleNamespace(discounted=_discounted(discounted_gross))


def _item(
    *,
    product_id: int = 1,
    product_name: str = "Widget",
    price_at_add_time: str,
):
    return SimpleNamespace(
        product_id=product_id,
        product=SimpleNamespace(name=product_name),
        price_at_add_time=Decimal(price_at_add_time),
    )


def _line(
    *,
    price_at_add_time: str,
    current_gross: str | None,
    product_id: int = 1,
    product_name: str = "Widget",
):
    """Build a CartLinePricingResult-like stub.

    ``current_gross=None`` simulates an unmigrated product (unit_pricing=None).
    """
    return SimpleNamespace(
        item=_item(
            product_id=product_id,
            product_name=product_name,
            price_at_add_time=price_at_add_time,
        ),
        unit_pricing=_unit_pricing(current_gross) if current_gross is not None else None,
    )


def _cart_pricing(*lines):
    """Wrap lines into a CartTotalsResult-like stub."""
    return SimpleNamespace(items=list(lines))


# ---------------------------------------------------------------------------
# Severity classification — no change
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_price_change_returns_none():
    """When price_at_add_time == current gross, severity is NONE."""
    cp = _cart_pricing(_line(price_at_add_time="100.00", current_gross="100.00"))
    summary = detect_price_changes(cp)

    assert summary.has_changes is False
    assert summary.severity == PriceChangeSeverity.NONE
    assert summary.affected_items == 0
    assert summary.items == []


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_change_below_info_threshold_is_none():
    """A 0.5 % change is below the 1 % INFO threshold → NONE."""
    # 100 → 100.50 = 0.5 % increase
    cp = _cart_pricing(_line(price_at_add_time="100.00", current_gross="100.50"))
    summary = detect_price_changes(cp)

    assert summary.has_changes is False
    assert summary.severity == PriceChangeSeverity.NONE
    assert summary.affected_items == 0


# ---------------------------------------------------------------------------
# Severity classification — INFO
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_change_at_info_threshold_is_info():
    """Exactly 1 % change (== INFO threshold) is classified as INFO."""
    # 100 → 101 = exactly 1 %
    cp = _cart_pricing(_line(price_at_add_time="100.00", current_gross="101.00"))
    summary = detect_price_changes(cp)

    assert summary.has_changes is True
    assert summary.severity == PriceChangeSeverity.INFO
    assert summary.affected_items == 1
    item = summary.items[0]
    assert item.severity == PriceChangeSeverity.INFO
    assert item.direction == PriceChangeDirection.UP


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_change_above_info_below_warning_is_info():
    """A 3 % change is above INFO (1 %) but below WARNING (5 %) → INFO."""
    # 100 → 103 = 3 %
    cp = _cart_pricing(_line(price_at_add_time="100.00", current_gross="103.00"))
    summary = detect_price_changes(cp)

    assert summary.has_changes is True
    assert summary.severity == PriceChangeSeverity.INFO
    assert summary.items[0].percent_change == Decimal("3.00")


# ---------------------------------------------------------------------------
# Severity classification — WARNING
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_change_at_warning_threshold_is_warning():
    """Exactly 5 % change (== WARNING threshold) is classified as WARNING."""
    # 100 → 105 = exactly 5 %
    cp = _cart_pricing(_line(price_at_add_time="100.00", current_gross="105.00"))
    summary = detect_price_changes(cp)

    assert summary.has_changes is True
    assert summary.severity == PriceChangeSeverity.WARNING
    assert summary.items[0].severity == PriceChangeSeverity.WARNING


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_change_above_warning_threshold_is_warning():
    """A 20 % change is above the WARNING threshold → WARNING."""
    cp = _cart_pricing(_line(price_at_add_time="100.00", current_gross="120.00"))
    summary = detect_price_changes(cp)

    assert summary.severity == PriceChangeSeverity.WARNING
    assert summary.items[0].percent_change == Decimal("20.00")


# ---------------------------------------------------------------------------
# Direction
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_price_increase_direction_is_up():
    """A price that went up has direction=UP and a positive absolute_change."""
    cp = _cart_pricing(_line(price_at_add_time="100.00", current_gross="110.00"))
    summary = detect_price_changes(cp)

    item = summary.items[0]
    assert item.direction == PriceChangeDirection.UP
    assert item.absolute_change == Decimal("10.00")
    assert item.old_unit_gross == Decimal("100.00")
    assert item.new_unit_gross == Decimal("110.00")


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_price_decrease_direction_is_down():
    """A price that went down has direction=DOWN and a negative absolute_change."""
    cp = _cart_pricing(_line(price_at_add_time="100.00", current_gross="90.00"))
    summary = detect_price_changes(cp)

    item = summary.items[0]
    assert item.direction == PriceChangeDirection.DOWN
    assert item.absolute_change == Decimal("-10.00")
    assert item.percent_change == Decimal("10.00")  # unsigned


# ---------------------------------------------------------------------------
# Unmigrated product safety
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unmigrated_line_is_skipped_safely():
    """Lines with unit_pricing=None (unmigrated product) are excluded silently."""
    cp = _cart_pricing(
        _line(price_at_add_time="100.00", current_gross=None),
    )
    summary = detect_price_changes(cp)

    assert summary.has_changes is False
    assert summary.severity == PriceChangeSeverity.NONE
    assert summary.affected_items == 0


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_mixed_migrated_and_unmigrated_only_migrated_contributes():
    """Unmigrated lines are ignored; migrated lines with changes are reported."""
    cp = _cart_pricing(
        _line(price_at_add_time="100.00", current_gross=None, product_id=1),  # unmigrated
        _line(price_at_add_time="50.00", current_gross="55.00", product_id=2),  # +10%
    )
    summary = detect_price_changes(cp)

    assert summary.has_changes is True
    assert summary.affected_items == 1
    assert summary.items[0].product_id == 2


# ---------------------------------------------------------------------------
# Cart-level aggregation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_cart_level_severity_is_highest_across_lines():
    """Cart-level severity reflects the most severe single line change."""
    cp = _cart_pricing(
        _line(price_at_add_time="100.00", current_gross="102.00", product_id=1),  # 2% → INFO
        _line(price_at_add_time="100.00", current_gross="115.00", product_id=2),  # 15% → WARNING
    )
    summary = detect_price_changes(cp)

    assert summary.severity == PriceChangeSeverity.WARNING
    assert summary.affected_items == 2


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_affected_items_counts_only_lines_that_exceed_threshold():
    """Lines below the INFO threshold do not appear in affected_items count."""
    cp = _cart_pricing(
        _line(price_at_add_time="100.00", current_gross="100.20", product_id=1),  # 0.2% → NONE
        _line(price_at_add_time="100.00", current_gross="103.00", product_id=2),  # 3% → INFO
    )
    summary = detect_price_changes(cp)

    assert summary.affected_items == 1
    assert summary.items[0].product_id == 2


# ---------------------------------------------------------------------------
# Threshold guard — warning < info is normalised
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=10,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=2,  # invalid: warn < info
)
def test_warning_threshold_below_info_is_normalised():
    """When warning < info in settings, warning is lifted to equal info.

    A 5 % change should be classified as WARNING (normalised warn=info=10 %)
    — since 5 % < 10 %, it actually comes out as NONE.
    """
    cp = _cart_pricing(_line(price_at_add_time="100.00", current_gross="105.00"))
    summary = detect_price_changes(cp)

    # 5 % < normalised warn (10 %) → INFO would require >= 10 %, so NONE here
    assert summary.severity == PriceChangeSeverity.NONE


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT=1,
    CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT=5,
)
def test_serialize_price_change_summary_shape():
    """serialize_price_change_summary returns a stable JSON-safe dict."""
    cp = _cart_pricing(
        _line(
            price_at_add_time="100.00",
            current_gross="110.00",
            product_id=42,
            product_name="Widget",
        )
    )
    summary = detect_price_changes(cp)
    data = serialize_price_change_summary(summary)

    assert data["has_changes"] is True
    assert data["severity"] == "WARNING"
    assert data["affected_items"] == 1

    item = data["items"][0]
    assert item["product_id"] == 42
    assert item["product_name"] == "Widget"
    assert item["old_unit_gross"] == "100.00"
    assert item["new_unit_gross"] == "110.00"
    assert item["absolute_change"] == "10.00"
    assert item["percent_change"] == "10.00"
    assert item["direction"] == "UP"
    assert item["severity"] == "WARNING"


@pytest.mark.django_db
def test_serialize_no_changes_empty_items_list():
    """When has_changes is False, items list is empty in the serialised form."""
    cp = _cart_pricing(_line(price_at_add_time="50.00", current_gross="50.00"))
    summary = detect_price_changes(cp)
    data = serialize_price_change_summary(summary)

    assert data["has_changes"] is False
    assert data["items"] == []
    assert data["affected_items"] == 0
