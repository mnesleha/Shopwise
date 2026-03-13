"""Unit tests for Phase 4 / Slice 3 — auto-apply order-level promotion resolver.

Covers:
- Returns None when no promotions exist
- Returns None when promotion is inactive (is_active=False)
- Returns None when cart_gross < minimum_order_value
- Returns promotion when cart_gross == minimum_order_value (boundary)
- Returns promotion when cart_gross > minimum_order_value
- Returns promotion when minimum_order_value is None (always eligible)
- Ignores CAMPAIGN_APPLY and MANUAL_ENTRY promotions
- Active window filtering: active_from, active_to, NULL bounds
- Winner selection: highest priority wins
- Tie-break: lowest id wins when priority is equal
- Expired promotions are ignored
- Future promotions are ignored
- PERCENT and FIXED type promotions are both resolved
"""

import pytest
from decimal import Decimal
from django.utils.timezone import now, timedelta

from discounts.models import AcquisitionMode, OrderPromotion, PromotionType, StackingPolicy
from discounts.services.auto_apply_resolver import resolve_auto_apply_order_promotion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CODE_SEQ = 0


def _next_code() -> str:
    global _CODE_SEQ
    _CODE_SEQ += 1
    return f"PROMO-{_CODE_SEQ:04d}"


def make_auto_apply_promotion(**kwargs) -> OrderPromotion:
    """Create a valid AUTO_APPLY OrderPromotion with sensible defaults."""
    defaults = {
        "name": "Auto Promo",
        "code": _next_code(),
        "type": PromotionType.PERCENT,
        "value": Decimal("10"),
        "acquisition_mode": AcquisitionMode.AUTO_APPLY,
        "stacking_policy": StackingPolicy.EXCLUSIVE,
        "priority": 5,
        "is_active": True,
        "minimum_order_value": None,
        "active_from": None,
        "active_to": None,
    }
    defaults.update(kwargs)
    return OrderPromotion.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Basic resolution
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestResolveAutoApply:

    def test_returns_none_when_no_promotions_exist(self):
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result is None

    def test_returns_none_when_promotion_is_inactive(self):
        make_auto_apply_promotion(is_active=False)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result is None

    def test_returns_promotion_for_eligible_cart(self):
        promo = make_auto_apply_promotion()
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("50.00"), currency="EUR"
        )
        assert result == promo

    def test_ignores_campaign_apply_acquisition_mode(self):
        make_auto_apply_promotion(acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result is None

    def test_ignores_manual_entry_acquisition_mode(self):
        make_auto_apply_promotion(acquisition_mode=AcquisitionMode.MANUAL_ENTRY)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result is None


# ---------------------------------------------------------------------------
# minimum_order_value eligibility
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMinimumOrderValue:

    def test_eligible_when_minimum_order_value_is_none(self):
        promo = make_auto_apply_promotion(minimum_order_value=None)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("1.00"), currency="EUR"
        )
        assert result == promo

    def test_eligible_when_cart_gross_equals_minimum(self):
        promo = make_auto_apply_promotion(minimum_order_value=Decimal("100.00"))
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result == promo

    def test_eligible_when_cart_gross_exceeds_minimum(self):
        promo = make_auto_apply_promotion(minimum_order_value=Decimal("100.00"))
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("150.00"), currency="EUR"
        )
        assert result == promo

    def test_not_eligible_when_cart_gross_below_minimum(self):
        make_auto_apply_promotion(minimum_order_value=Decimal("100.00"))
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("99.99"), currency="EUR"
        )
        assert result is None

    def test_returns_none_when_all_promotions_below_threshold(self):
        make_auto_apply_promotion(
            minimum_order_value=Decimal("200.00"), priority=10
        )
        make_auto_apply_promotion(
            minimum_order_value=Decimal("150.00"), priority=5
        )
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result is None

    def test_skips_ineligible_falls_through_to_eligible_lower_priority(self):
        """When the highest-priority promo is over threshold, the next eligible one wins."""
        make_auto_apply_promotion(
            minimum_order_value=Decimal("500.00"), priority=10
        )
        lower = make_auto_apply_promotion(
            minimum_order_value=Decimal("50.00"), priority=5
        )
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result == lower


# ---------------------------------------------------------------------------
# Active time window filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestActiveTimeWindow:

    def test_active_when_both_bounds_are_null(self):
        promo = make_auto_apply_promotion(active_from=None, active_to=None)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result == promo

    def test_active_when_active_from_in_past(self):
        past = now() - timedelta(days=1)
        promo = make_auto_apply_promotion(active_from=past, active_to=None)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result == promo

    def test_active_when_active_to_in_future(self):
        future = now() + timedelta(days=1)
        promo = make_auto_apply_promotion(active_from=None, active_to=future)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result == promo

    def test_not_active_when_active_from_in_future(self):
        future = now() + timedelta(days=1)
        make_auto_apply_promotion(active_from=future, active_to=None)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result is None

    def test_not_active_when_active_to_in_past(self):
        past = now() - timedelta(days=1)
        make_auto_apply_promotion(active_from=None, active_to=past)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result is None

    def test_not_active_when_both_bounds_expired(self):
        past_from = now() - timedelta(days=10)
        past_to = now() - timedelta(days=5)
        make_auto_apply_promotion(active_from=past_from, active_to=past_to)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result is None


# ---------------------------------------------------------------------------
# Winner selection: priority and tie-break
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWinnerSelection:

    def test_highest_priority_wins(self):
        low_priority = make_auto_apply_promotion(priority=3)
        high_priority = make_auto_apply_promotion(priority=10)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result == high_priority
        assert result != low_priority

    def test_lowest_id_wins_on_priority_tie(self):
        """When two promotions share the same priority, the one created first (lowest id) wins."""
        first = make_auto_apply_promotion(priority=5)
        second = make_auto_apply_promotion(priority=5)
        assert first.id < second.id
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result == first

    def test_returns_single_winner_not_a_list(self):
        make_auto_apply_promotion(priority=5)
        make_auto_apply_promotion(priority=5)
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert isinstance(result, OrderPromotion)


# ---------------------------------------------------------------------------
# Promotion type (PERCENT / FIXED)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPromotionTypes:

    def test_percent_type_promotion_is_returned(self):
        promo = make_auto_apply_promotion(type=PromotionType.PERCENT, value=Decimal("15"))
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result == promo
        assert result.type == PromotionType.PERCENT

    def test_fixed_type_promotion_is_returned(self):
        promo = make_auto_apply_promotion(type=PromotionType.FIXED, value=Decimal("10.00"))
        result = resolve_auto_apply_order_promotion(
            cart_gross=Decimal("100.00"), currency="EUR"
        )
        assert result == promo
        assert result.type == PromotionType.FIXED
