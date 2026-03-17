"""Unit tests for Phase 4 / Slice 1 — order-level discount domain model.

Covers:
- OrderPromotion creation (happy path, all acquisition modes)
- Validation rules: value, percent ceiling, date window, minimum_order_value
- is_currently_active() helper
- AcquisitionMode and StackingPolicy semantics at model level
- Offer entity: creation, token uniqueness, FK linkage, lifecycle status
- Offer validation: blank token, date window
- Reference scenarios: auto-apply, threshold, campaign, owned-media
- Invalid model/field combinations are rejected
- Admin registration sanity checks
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils.timezone import now

from discounts.admin import OfferAdmin, OrderPromotionAdmin
from discounts.models import (
    AcquisitionMode,
    Offer,
    OfferStatus,
    OrderPromotion,
    PromotionType,
    StackingPolicy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_order_promotion(**kwargs) -> OrderPromotion:
    defaults = {
        "name": "Order Discount",
        "code": "order-discount-2026",
        "type": PromotionType.PERCENT,
        "value": 10,
        "acquisition_mode": AcquisitionMode.AUTO_APPLY,
        "stacking_policy": StackingPolicy.EXCLUSIVE,
        "priority": 5,
        "is_active": True,
    }
    defaults.update(kwargs)
    return OrderPromotion.objects.create(**defaults)


def make_offer(promotion: OrderPromotion, **kwargs) -> Offer:
    defaults = {
        "token": "SUMMER10",
        "promotion": promotion,
        "status": OfferStatus.CREATED,
        "is_active": True,
    }
    defaults.update(kwargs)
    return Offer.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Basic creation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_promotion_can_be_created():
    promo = make_order_promotion()

    assert promo.pk is not None
    assert promo.code == "order-discount-2026"
    assert str(promo) == "Order Discount (order-discount-2026)"


@pytest.mark.django_db
def test_order_promotion_str_includes_code():
    promo = make_order_promotion(name="Winter Deal", code="winter-deal-2026")
    assert "Winter Deal" in str(promo)
    assert "winter-deal-2026" in str(promo)


@pytest.mark.django_db
def test_order_promotion_code_is_unique():
    make_order_promotion(code="unique-order-code")
    with pytest.raises(IntegrityError):
        OrderPromotion.objects.create(
            name="Duplicate",
            code="unique-order-code",
            type=PromotionType.PERCENT,
            value=5,
        )


@pytest.mark.django_db
def test_order_promotion_defaults():
    promo = make_order_promotion(code="defaults-test")
    assert promo.acquisition_mode == AcquisitionMode.AUTO_APPLY
    assert promo.stacking_policy == StackingPolicy.EXCLUSIVE
    assert promo.is_active is True
    assert promo.is_discoverable is False
    assert promo.minimum_order_value is None


# ---------------------------------------------------------------------------
# Acquisition mode
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_promotion_auto_apply_mode():
    promo = make_order_promotion(
        code="auto-apply-test",
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
    )
    assert promo.acquisition_mode == AcquisitionMode.AUTO_APPLY


@pytest.mark.django_db
def test_order_promotion_campaign_apply_mode():
    promo = make_order_promotion(
        code="campaign-test",
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
    )
    assert promo.acquisition_mode == AcquisitionMode.CAMPAIGN_APPLY


@pytest.mark.django_db
def test_order_promotion_manual_entry_mode():
    promo = make_order_promotion(
        code="manual-test",
        acquisition_mode=AcquisitionMode.MANUAL_ENTRY,
    )
    assert promo.acquisition_mode == AcquisitionMode.MANUAL_ENTRY


# ---------------------------------------------------------------------------
# Stacking policy
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_promotion_exclusive_stacking():
    promo = make_order_promotion(
        code="exclusive-test",
        stacking_policy=StackingPolicy.EXCLUSIVE,
    )
    assert promo.stacking_policy == StackingPolicy.EXCLUSIVE


@pytest.mark.django_db
def test_order_promotion_stackable_with_line():
    promo = make_order_promotion(
        code="stackable-test",
        stacking_policy=StackingPolicy.STACKABLE_WITH_LINE,
    )
    assert promo.stacking_policy == StackingPolicy.STACKABLE_WITH_LINE


# ---------------------------------------------------------------------------
# Validation — value
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_promotion_value_must_be_positive():
    promo = OrderPromotion(
        name="Bad Promo",
        code="bad-value-order",
        type=PromotionType.PERCENT,
        value=0,
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "value" in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_promotion_negative_value_is_invalid():
    promo = OrderPromotion(
        name="Negative Promo",
        code="neg-value-order",
        type=PromotionType.PERCENT,
        value=-5,
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "value" in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_promotion_percent_cannot_exceed_100():
    promo = OrderPromotion(
        name="Over Promo",
        code="over-100-order",
        type=PromotionType.PERCENT,
        value=101,
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "value" in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_promotion_percent_exactly_100_is_valid():
    promo = OrderPromotion(
        name="Full Promo",
        code="full-100-order",
        type=PromotionType.PERCENT,
        value=100,
    )
    promo.full_clean()  # must not raise


@pytest.mark.django_db
def test_order_promotion_fixed_large_value_is_valid():
    promo = OrderPromotion(
        name="Big Fixed",
        code="big-fixed-order",
        type=PromotionType.FIXED,
        value=500,
    )
    promo.full_clean()  # must not raise


# ---------------------------------------------------------------------------
# Validation — active window
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_promotion_active_from_after_active_to_is_invalid():
    today = now().date()
    promo = OrderPromotion(
        name="Bad Window",
        code="bad-window-order",
        type=PromotionType.PERCENT,
        value=10,
        active_from=today,
        active_to=today.replace(year=today.year - 1),
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "active_from" in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_promotion_active_from_equals_active_to_is_valid():
    today = now().date()
    promo = OrderPromotion(
        name="Single Day",
        code="single-day-order",
        type=PromotionType.PERCENT,
        value=10,
        active_from=today,
        active_to=today,
    )
    promo.full_clean()  # must not raise


@pytest.mark.django_db
def test_order_promotion_missing_dates_is_valid():
    promo = OrderPromotion(
        name="No Window",
        code="no-window-order",
        type=PromotionType.PERCENT,
        value=10,
    )
    promo.full_clean()  # must not raise


# ---------------------------------------------------------------------------
# Validation — minimum_order_value
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_promotion_minimum_order_value_zero_is_invalid():
    promo = OrderPromotion(
        name="Zero Threshold",
        code="zero-threshold",
        type=PromotionType.PERCENT,
        value=10,
        minimum_order_value=0,
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "minimum_order_value" in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_promotion_minimum_order_value_negative_is_invalid():
    promo = OrderPromotion(
        name="Neg Threshold",
        code="neg-threshold",
        type=PromotionType.PERCENT,
        value=10,
        minimum_order_value=-50,
    )
    with pytest.raises(ValidationError) as exc_info:
        promo.full_clean()
    assert "minimum_order_value" in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_promotion_minimum_order_value_positive_is_valid():
    promo = OrderPromotion(
        name="Good Threshold",
        code="good-threshold",
        type=PromotionType.PERCENT,
        value=10,
        minimum_order_value=100,
    )
    promo.full_clean()  # must not raise


# ---------------------------------------------------------------------------
# is_currently_active()
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_promotion_is_currently_active_no_dates():
    promo = make_order_promotion(code="active-no-dates", is_active=True)
    assert promo.is_currently_active() is True


@pytest.mark.django_db
def test_order_promotion_is_not_active_when_disabled():
    promo = make_order_promotion(code="disabled-order", is_active=False)
    assert promo.is_currently_active() is False


@pytest.mark.django_db
def test_order_promotion_is_not_active_before_window():
    today = now().date()
    promo = make_order_promotion(
        code="future-order",
        is_active=True,
        active_from=today.replace(year=today.year + 1),
    )
    assert promo.is_currently_active() is False


@pytest.mark.django_db
def test_order_promotion_is_not_active_after_window():
    today = now().date()
    promo = make_order_promotion(
        code="expired-order",
        is_active=True,
        active_to=today.replace(year=today.year - 1),
    )
    assert promo.is_currently_active() is False


@pytest.mark.django_db
def test_order_promotion_is_active_within_window():
    today = now().date()
    promo = make_order_promotion(
        code="in-window-order",
        is_active=True,
        active_from=today.replace(year=today.year - 1),
        active_to=today.replace(year=today.year + 1),
    )
    assert promo.is_currently_active() is True


# ---------------------------------------------------------------------------
# Offer — basic creation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_offer_can_be_created():
    promo = make_order_promotion(code="offer-promo")
    offer = make_offer(promo, token="PROMO10")

    assert offer.pk is not None
    assert offer.token == "PROMO10"
    assert offer.status == OfferStatus.CREATED
    assert str(offer) == "PROMO10 → offer-promo"


@pytest.mark.django_db
def test_offer_default_status_is_created():
    promo = make_order_promotion(code="status-default-promo")
    offer = make_offer(promo, token="NEWCODE")
    assert offer.status == OfferStatus.CREATED


@pytest.mark.django_db
def test_offer_token_is_unique():
    promo = make_order_promotion(code="token-unique-promo")
    make_offer(promo, token="UNIQUE10")
    with pytest.raises(IntegrityError):
        Offer.objects.create(
            token="UNIQUE10",
            promotion=promo,
            status=OfferStatus.CREATED,
            is_active=True,
        )


@pytest.mark.django_db
def test_offer_linked_to_promotion():
    promo = make_order_promotion(code="linked-promo")
    offer = make_offer(promo, token="LINK10")

    assert offer.promotion == promo
    assert promo.offers.count() == 1


@pytest.mark.django_db
def test_offer_promotion_has_multiple_offers():
    promo = make_order_promotion(code="multi-offer-promo")
    make_offer(promo, token="CODE1")
    make_offer(promo, token="CODE2")

    assert promo.offers.count() == 2


# ---------------------------------------------------------------------------
# Offer — lifecycle status values
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_offer_all_status_values_are_settable():
    promo = make_order_promotion(code="lifecycle-promo")
    for i, status in enumerate(OfferStatus.values):
        offer = Offer.objects.create(
            token=f"STATUS{i}",
            promotion=promo,
            status=status,
            is_active=True,
        )
        assert offer.status == status


# ---------------------------------------------------------------------------
# Offer — validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_offer_blank_token_is_invalid():
    promo = make_order_promotion(code="blank-token-promo")
    offer = Offer(
        token="   ",
        promotion=promo,
        is_active=True,
    )
    with pytest.raises(ValidationError) as exc_info:
        offer.full_clean()
    assert "token" in exc_info.value.message_dict


@pytest.mark.django_db
def test_offer_active_window_inversion_is_invalid():
    today = now().date()
    promo = make_order_promotion(code="window-offer-promo")
    offer = Offer(
        token="BADWINDOW",
        promotion=promo,
        is_active=True,
        active_from=today,
        active_to=today.replace(year=today.year - 1),
    )
    with pytest.raises(ValidationError) as exc_info:
        offer.full_clean()
    assert "active_from" in exc_info.value.message_dict


@pytest.mark.django_db
def test_offer_valid_window_is_accepted():
    today = now().date()
    promo = make_order_promotion(code="valid-window-offer")
    offer = Offer(
        token="GOODWINDOW",
        promotion=promo,
        is_active=True,
        active_from=today,
        active_to=today.replace(year=today.year + 1),
    )
    offer.full_clean()  # must not raise


# ---------------------------------------------------------------------------
# Offer — is_currently_active()
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_offer_is_currently_active_no_dates():
    promo = make_order_promotion(code="offer-active-no-dates")
    offer = make_offer(promo, token="ACTIVE10", is_active=True)
    assert offer.is_currently_active() is True


@pytest.mark.django_db
def test_offer_is_not_active_when_disabled():
    promo = make_order_promotion(code="offer-disabled-promo")
    offer = make_offer(promo, token="OFF10", is_active=False)
    assert offer.is_currently_active() is False


@pytest.mark.django_db
def test_offer_is_not_active_before_window():
    today = now().date()
    promo = make_order_promotion(code="offer-future-promo")
    offer = make_offer(
        promo,
        token="FUTURE10",
        is_active=True,
        active_from=today.replace(year=today.year + 1),
    )
    assert offer.is_currently_active() is False


@pytest.mark.django_db
def test_offer_is_not_active_after_window():
    today = now().date()
    promo = make_order_promotion(code="offer-expired-promo")
    offer = make_offer(
        promo,
        token="EXP10",
        is_active=True,
        active_to=today.replace(year=today.year - 1),
    )
    assert offer.is_currently_active() is False


# ---------------------------------------------------------------------------
# Reference scenario 1: on-site auto-apply order discount
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scenario_auto_apply_order_discount():
    """Scenario 1: platform auto-applies discount, no token required."""
    promo = make_order_promotion(
        code="site-wide-10pct",
        name="Site-wide 10% off",
        type=PromotionType.PERCENT,
        value=10,
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        is_active=True,
    )
    assert promo.acquisition_mode == AcquisitionMode.AUTO_APPLY
    assert promo.is_currently_active() is True
    # AUTO_APPLY promotions do not require an Offer token — no offers needed
    assert promo.offers.count() == 0


# ---------------------------------------------------------------------------
# Reference scenario 2: threshold / progress reward
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scenario_threshold_reward():
    """Scenario 2: free shipping / discount when cart exceeds threshold."""
    promo = make_order_promotion(
        code="threshold-200-free-ship",
        name="Free shipping over 200",
        type=PromotionType.FIXED,
        value=15,
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
        minimum_order_value=200,
        stacking_policy=StackingPolicy.STACKABLE_WITH_LINE,
        is_active=True,
    )
    assert promo.minimum_order_value == 200
    assert promo.acquisition_mode == AcquisitionMode.AUTO_APPLY
    assert promo.stacking_policy == StackingPolicy.STACKABLE_WITH_LINE


# ---------------------------------------------------------------------------
# Reference scenario 3: campaign-applied offer (email / URL / UTM)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scenario_campaign_offer():
    """Scenario 3: offer delivered via email link or UTM campaign."""
    promo = make_order_promotion(
        code="email-campaign-q1",
        name="Q1 Email Campaign 15% off",
        type=PromotionType.PERCENT,
        value=15,
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        is_active=True,
    )
    # Campaign delivers an Offer token to the customer
    offer = make_offer(promo, token="Q1MAIL15", is_active=True)

    assert promo.acquisition_mode == AcquisitionMode.CAMPAIGN_APPLY
    assert offer.token == "Q1MAIL15"
    assert offer.promotion == promo
    assert offer.is_currently_active() is True


# ---------------------------------------------------------------------------
# Reference scenario 4: owned-media contextual promotion (discoverable)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scenario_owned_media_discoverable_promotion():
    """Scenario 4: promotion surfaced as active benefit in-product (loyalty banner etc.)."""
    promo = make_order_promotion(
        code="loyalty-benefit-spring",
        name="Spring loyalty benefit",
        type=PromotionType.PERCENT,
        value=5,
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
        is_discoverable=True,
        is_active=True,
    )
    assert promo.is_discoverable is True
    assert promo.is_currently_active() is True


# ---------------------------------------------------------------------------
# Admin sanity checks
# ---------------------------------------------------------------------------


def test_order_promotion_admin_is_registered():
    site = AdminSite()
    admin_instance = OrderPromotionAdmin(OrderPromotion, site)
    assert admin_instance is not None


def test_order_promotion_admin_has_offer_inline():
    from discounts.admin import OfferInline

    site = AdminSite()
    admin_instance = OrderPromotionAdmin(OrderPromotion, site)
    inline_models = [inline.model for inline in admin_instance.inlines]
    assert Offer in inline_models


def test_offer_admin_is_registered():
    site = AdminSite()
    admin_instance = OfferAdmin(Offer, site)
    assert admin_instance is not None
