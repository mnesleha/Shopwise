"""Admin smoke tests for discounts — Phase 4 merchant-clarity slice.

Covers:
- OrderPromotionAdmin list-column helpers (discount_display, threshold_display)
- OfferAdmin list-column helpers (promotion_link, promotion_discount_display)
- Admin registration (both models appear in the admin site)
- Fieldset structure and help_text wiring
- send_offer_email action guards
"""

from decimal import Decimal

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from rest_framework.test import APIClient

from discounts.admin import (
    OfferAdmin,
    OrderPromotionAdmin,
    _format_value,
)
from discounts.models import (
    AcquisitionMode,
    Offer,
    OfferStatus,
    OrderPromotion,
    PromotionType,
    StackingPolicy,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def site():
    return AdminSite()


@pytest.fixture
def order_promo_admin(site):
    return OrderPromotionAdmin(OrderPromotion, site)


@pytest.fixture
def offer_admin(site):
    return OfferAdmin(Offer, site)


@pytest.fixture
def rf():
    return RequestFactory()


def _make_promo(
    *,
    name: str = "Test Promo",
    code: str = "test-promo",
    promo_type: str = PromotionType.FIXED,
    value: Decimal = Decimal("50.00"),
    acquisition_mode: str = AcquisitionMode.AUTO_APPLY,
    minimum_order_value: Decimal | None = None,
    priority: int = 0,
) -> "OrderPromotion":
    return OrderPromotion.objects.create(
        name=name,
        code=code,
        type=promo_type,
        value=value,
        acquisition_mode=acquisition_mode,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=priority,
        is_active=True,
        minimum_order_value=minimum_order_value,
    )


def _make_offer(promo: "OrderPromotion", token: str = "TEST-TOKEN") -> "Offer":
    return Offer.objects.create(
        token=token,
        promotion=promo,
        status=OfferStatus.CREATED,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# _format_value helper
# ---------------------------------------------------------------------------


def test_format_value_fixed():
    """FIXED promotions display as '€X.XX'."""
    promo = OrderPromotion(type=PromotionType.FIXED, value=Decimal("50.00"))
    assert _format_value(promo) == "€50.00"


def test_format_value_percent():
    """PERCENT promotions display as 'X%'."""
    promo = OrderPromotion(type=PromotionType.PERCENT, value=Decimal("10"))
    assert _format_value(promo) == "10%"


def test_format_value_percent_strips_trailing_zero():
    """PERCENT value displayed without unnecessary decimal places."""
    promo = OrderPromotion(type=PromotionType.PERCENT, value=Decimal("15.00"))
    assert _format_value(promo) == "15%"


# ---------------------------------------------------------------------------
# OrderPromotionAdmin list-column helpers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_discount_display_fixed(order_promo_admin):
    """discount_display returns 'Fixed €50.00' for a FIXED promotion."""
    promo = _make_promo(promo_type=PromotionType.FIXED, value=Decimal("50.00"))
    assert order_promo_admin.discount_display(promo) == "Fixed €50.00"


@pytest.mark.django_db
def test_discount_display_percent(order_promo_admin):
    """discount_display returns 'Percent 10%' for a PERCENT promotion."""
    promo = _make_promo(
        code="pct-promo",
        promo_type=PromotionType.PERCENT,
        value=Decimal("10"),
    )
    assert order_promo_admin.discount_display(promo) == "Percent 10%"


@pytest.mark.django_db
def test_threshold_display_when_set(order_promo_admin):
    """threshold_display returns formatted amount when minimum_order_value is set."""
    promo = _make_promo(
        code="threshold-promo",
        minimum_order_value=Decimal("200.00"),
    )
    assert order_promo_admin.threshold_display(promo) == "€200.00"


@pytest.mark.django_db
def test_threshold_display_when_absent(order_promo_admin):
    """threshold_display returns '—' when minimum_order_value is None."""
    promo = _make_promo(code="no-threshold-promo")
    assert order_promo_admin.threshold_display(promo) == "—"


# ---------------------------------------------------------------------------
# OfferAdmin list-column helpers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_offer_promotion_link(offer_admin):
    """promotion_link returns 'Promo Name (promo-code)'."""
    promo = _make_promo(name="Spring Sale", code="spring-sale")
    offer = _make_offer(promo, token="SPRING-001")
    assert offer_admin.promotion_link(offer) == "Spring Sale (spring-sale)"


@pytest.mark.django_db
def test_offer_promotion_discount_display_fixed(offer_admin):
    """promotion_discount_display returns discount summary for FIXED."""
    promo = _make_promo(
        code="fixed-offer-promo", promo_type=PromotionType.FIXED, value=Decimal("30.00")
    )
    offer = _make_offer(promo, token="FIXED-TOK")
    assert offer_admin.promotion_discount_display(offer) == "Fixed €30.00"


@pytest.mark.django_db
def test_offer_promotion_discount_display_percent(offer_admin):
    """promotion_discount_display returns discount summary for PERCENT."""
    promo = _make_promo(
        code="pct-offer-promo",
        promo_type=PromotionType.PERCENT,
        value=Decimal("20"),
    )
    offer = _make_offer(promo, token="PCT-TOK")
    assert offer_admin.promotion_discount_display(offer) == "Percent 20%"


# ---------------------------------------------------------------------------
# Admin fieldset & help_text wiring
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_promo_admin_fieldsets_include_key_sections(order_promo_admin, rf):
    """All expected fieldset titles are present in OrderPromotionAdmin."""
    expected_titles = {
        "Promotion basics",
        "Discount",
        "How the customer receives it",
        "Qualification / minimum order",
        "Exclusivity",
        "Customer visibility",
        "Advanced — Priority",
        "Scheduling",
        "Internal notes",
    }
    actual_titles = {fs[0] for fs in order_promo_admin.fieldsets}
    assert expected_titles == actual_titles


@pytest.mark.django_db
def test_order_promo_admin_get_form_injects_priority_help(order_promo_admin, rf):
    """get_form() injects help text for the 'priority' field."""
    promo = _make_promo(code="help-text-promo")
    request = rf.get("/")
    request.user = None  # help_text inspection does not require auth
    form_class = order_promo_admin.get_form(request, obj=promo)
    assert "priority" in form_class.base_fields
    help_text = str(form_class.base_fields["priority"].help_text)
    assert "tiebreak" in help_text.lower() or "tied" in help_text.lower() or "tie" in help_text.lower()


@pytest.mark.django_db
def test_order_promo_admin_get_form_injects_acquisition_mode_help(order_promo_admin, rf):
    """get_form() injects help text for the 'acquisition_mode' field."""
    promo = _make_promo(code="acq-help-promo")
    request = rf.get("/")
    request.user = None
    form_class = order_promo_admin.get_form(request, obj=promo)
    assert "acquisition_mode" in form_class.base_fields
    help_text = str(form_class.base_fields["acquisition_mode"].help_text)
    assert "auto" in help_text.lower()


@pytest.mark.django_db
def test_offer_admin_fieldsets_include_key_sections(offer_admin, rf):
    """All expected fieldset titles are present in OfferAdmin."""
    expected_titles = {"Offer token", "Status", "Validity window", "Internal notes"}
    actual_titles = {fs[0] for fs in offer_admin.fieldsets}
    assert expected_titles == actual_titles


@pytest.mark.django_db
def test_offer_admin_get_form_injects_token_help(offer_admin, rf):
    """get_form() injects help text for the 'token' field."""
    promo = _make_promo(
        code="offer-help-promo",
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
    )
    offer = _make_offer(promo, token="HELP-TOK")
    request = rf.get("/")
    request.user = None
    form_class = offer_admin.get_form(request, obj=offer)
    assert "token" in form_class.base_fields
    help_text = str(form_class.base_fields["token"].help_text)
    assert "unique" in help_text.lower() or "campaign" in help_text.lower()


# ---------------------------------------------------------------------------
# send_offer_email action guards
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_send_offer_email_rejects_multiple_selection(offer_admin, rf):
    """send_offer_email returns an error message when more than one offer is selected."""
    promo = _make_promo(
        code="multi-sel-promo",
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
    )
    offer1 = _make_offer(promo, token="TOK-MULTI-1")
    offer2 = _make_offer(promo, token="TOK-MULTI-2")

    request = rf.post("/")
    request.user = None
    request._messages = MockMessages()

    queryset = Offer.objects.filter(pk__in=[offer1.pk, offer2.pk])
    offer_admin.send_offer_email(request, queryset)

    assert request._messages.error_count == 1


@pytest.mark.django_db
def test_send_offer_email_rejects_non_campaign_promotion(offer_admin, rf):
    """send_offer_email returns an error when the promotion is not CAMPAIGN_APPLY."""
    promo = _make_promo(
        code="auto-apply-offer-promo",
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
    )
    offer = _make_offer(promo, token="AUTO-TOK")

    request = rf.post("/")
    request.user = None
    request._messages = MockMessages()

    queryset = Offer.objects.filter(pk=offer.pk)
    offer_admin.send_offer_email(request, queryset)

    assert request._messages.error_count == 1


# ---------------------------------------------------------------------------
# Admin site registration smoke test
# ---------------------------------------------------------------------------


def test_order_promotion_registered_in_admin():
    """OrderPromotion is registered in the default admin site."""
    from django.contrib import admin as django_admin

    assert OrderPromotion in django_admin.site._registry


def test_offer_registered_in_admin():
    """Offer is registered in the default admin site."""
    from django.contrib import admin as django_admin

    assert Offer in django_admin.site._registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockMessages:
    """Minimal message storage for admin action testing (no middleware needed)."""

    def __init__(self):
        self.error_count = 0

    def add(self, level, message, extra_tags=""):
        from django.contrib.messages import ERROR
        if level == ERROR:
            self.error_count += 1
