"""Tests for the guided campaign creation admin flow.

Phase 4 / Admin Slice 2.

Covers:
- GET campaign create view loads for admin users
- Form validation (invalid inputs rejected)
- POST creates OrderPromotion with CAMPAIGN_APPLY
- POST creates linked Offer automatically (token generated)
- POST triggers email sending path
- POST redirects to the new promotion change page on success
- Non-admin access is rejected
- CampaignCreateForm standalone validation
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from discounts.forms import CampaignCreateForm
from discounts.models import AcquisitionMode, Offer, OrderPromotion, PromotionType

User = get_user_model()

CAMPAIGN_URL = "/admin/discounts/orderpromotion/campaign/new/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="campaign_admin@example.com",
        password="secret123",
    )


@pytest.fixture
def admin_client(admin_user):
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def valid_post_data():
    """Minimal valid POST payload for the campaign creation form."""
    return {
        "name": "Spring 10% Off",
        "code": "spring-2026-10pct",
        "type": PromotionType.PERCENT,
        "value": "10.00",
        "recipient_email": "customer@example.com",
    }


# ---------------------------------------------------------------------------
# GET — view loads
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_campaign_create_view_get_returns_200(admin_client):
    """The campaign creation view loads for an authenticated admin user."""
    response = admin_client.get(CAMPAIGN_URL)
    assert response.status_code == 200


@pytest.mark.django_db
def test_campaign_create_view_contains_expected_heading(admin_client):
    """The campaign creation view page contains the expected heading text."""
    response = admin_client.get(CAMPAIGN_URL)
    content = response.content.decode()
    assert "Create and send campaign" in content


@pytest.mark.django_db
def test_campaign_create_view_contains_form_fields(admin_client):
    """The campaign creation view renders the key input fields."""
    response = admin_client.get(CAMPAIGN_URL)
    content = response.content.decode()
    assert 'name="name"' in content
    assert 'name="code"' in content
    assert 'name="type"' in content
    assert 'name="value"' in content
    assert 'name="recipient_email"' in content


@pytest.mark.django_db
def test_campaign_create_view_rejected_for_anonymous():
    """Anonymous users are redirected away from the campaign creation view."""
    client = Client()
    response = client.get(CAMPAIGN_URL)
    # Django admin redirects unauthenticated requests to the login page.
    assert response.status_code in (301, 302)
    assert "/admin/login/" in response["Location"] or "login" in response["Location"].lower()


# ---------------------------------------------------------------------------
# POST — valid submission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_valid_post_creates_order_promotion(admin_client, valid_post_data):
    """A valid POST creates an OrderPromotion with CAMPAIGN_APPLY mode."""
    with patch("discounts.services.campaign.send_campaign_offer_email"):
        admin_client.post(CAMPAIGN_URL, valid_post_data)

    assert OrderPromotion.objects.filter(code="spring-2026-10pct").exists()
    promo = OrderPromotion.objects.get(code="spring-2026-10pct")
    assert promo.name == "Spring 10% Off"
    assert promo.type == PromotionType.PERCENT
    assert promo.value == Decimal("10.00")
    assert promo.acquisition_mode == AcquisitionMode.CAMPAIGN_APPLY
    assert promo.is_active is True


@pytest.mark.django_db
def test_valid_post_creates_linked_offer(admin_client, valid_post_data):
    """A valid POST creates an Offer linked to the new OrderPromotion."""
    with patch("discounts.services.campaign.send_campaign_offer_email"):
        admin_client.post(CAMPAIGN_URL, valid_post_data)

    promo = OrderPromotion.objects.get(code="spring-2026-10pct")
    offers = Offer.objects.filter(promotion=promo)
    assert offers.count() == 1

    offer = offers.first()
    assert offer.token  # non-empty
    assert len(offer.token) == 32  # uuid4().hex is 32 chars
    assert offer.is_active is True


@pytest.mark.django_db
def test_valid_post_triggers_email_sending(admin_client, valid_post_data):
    """A valid POST calls send_campaign_offer_email with the correct arguments."""
    with patch("discounts.services.campaign.send_campaign_offer_email") as mock_send:
        admin_client.post(CAMPAIGN_URL, valid_post_data)

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["recipient_email"] == "customer@example.com"
    assert call_kwargs["promotion_name"] == "Spring 10% Off"
    assert "claim-offer?token=" in call_kwargs["offer_url"]


@pytest.mark.django_db
def test_valid_post_claim_url_contains_token(admin_client, valid_post_data):
    """The claim URL passed to the email function includes the generated token."""
    with patch("discounts.services.campaign.send_campaign_offer_email") as mock_send:
        admin_client.post(CAMPAIGN_URL, valid_post_data)

    offer = Offer.objects.filter(
        promotion__code="spring-2026-10pct"
    ).first()
    assert offer is not None
    call_kwargs = mock_send.call_args.kwargs
    assert offer.token in call_kwargs["offer_url"]


@pytest.mark.django_db
def test_valid_post_redirects_to_promotion_change_page(admin_client, valid_post_data):
    """A valid POST redirects to the newly created promotion's change page."""
    with patch("discounts.services.campaign.send_campaign_offer_email"):
        response = admin_client.post(CAMPAIGN_URL, valid_post_data)

    promo = OrderPromotion.objects.get(code="spring-2026-10pct")
    expected_url = reverse("admin:discounts_orderpromotion_change", args=[promo.pk])
    assert response.status_code == 302
    assert response["Location"] == expected_url


@pytest.mark.django_db
def test_valid_post_sets_success_message(admin_client, valid_post_data):
    """After a valid POST the success message includes promotion name and recipient."""
    with patch("discounts.services.campaign.send_campaign_offer_email"):
        response = admin_client.post(CAMPAIGN_URL, valid_post_data, follow=True)

    content = response.content.decode()
    assert "Spring 10% Off" in content
    assert "customer@example.com" in content


# ---------------------------------------------------------------------------
# POST — optional fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_valid_post_with_minimum_order_value(admin_client):
    """minimum_order_value is persisted when provided."""
    data = {
        "name": "Threshold Promo",
        "code": "threshold-promo",
        "type": PromotionType.FIXED,
        "value": "20.00",
        "minimum_order_value": "100.00",
        "recipient_email": "vip@example.com",
    }
    with patch("discounts.services.campaign.send_campaign_offer_email"):
        admin_client.post(CAMPAIGN_URL, data)

    promo = OrderPromotion.objects.get(code="threshold-promo")
    assert promo.minimum_order_value == Decimal("100.00")


@pytest.mark.django_db
def test_valid_post_offer_active_to_is_set(admin_client):
    """offer_active_to is persisted on the Offer when provided."""
    data = {
        "name": "Expiring Offer",
        "code": "expiring-offer",
        "type": PromotionType.PERCENT,
        "value": "5.00",
        "recipient_email": "someone@example.com",
        "offer_active_to": "2026-12-31",
    }
    with patch("discounts.services.campaign.send_campaign_offer_email"):
        admin_client.post(CAMPAIGN_URL, data)

    offer = Offer.objects.filter(promotion__code="expiring-offer").first()
    assert offer is not None
    import datetime
    assert offer.active_to == datetime.date(2026, 12, 31)


# ---------------------------------------------------------------------------
# POST — invalid inputs (form validation)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_invalid_post_missing_required_fields_returns_200(admin_client):
    """A POST with missing required fields re-renders the form (200, not redirect)."""
    with patch("discounts.services.campaign.send_campaign_offer_email"):
        response = admin_client.post(CAMPAIGN_URL, {})

    assert response.status_code == 200
    assert OrderPromotion.objects.count() == 0


@pytest.mark.django_db
def test_invalid_post_missing_email_shows_error(admin_client):
    """A POST with missing recipient_email re-renders with a field error."""
    data = {
        "name": "Bad Promo",
        "code": "bad-promo",
        "type": PromotionType.PERCENT,
        "value": "10.00",
        # recipient_email deliberately omitted
    }
    with patch("discounts.services.campaign.send_campaign_offer_email"):
        response = admin_client.post(CAMPAIGN_URL, data)

    content = response.content.decode()
    assert response.status_code == 200
    assert "recipient_email" in content or "Recipient email" in content
    assert OrderPromotion.objects.count() == 0


@pytest.mark.django_db
def test_invalid_post_percent_over_100_shows_error(admin_client):
    """A POST with a PERCENT value > 100 is rejected with a validation error."""
    data = {
        "name": "Too Much Off",
        "code": "too-much-off",
        "type": PromotionType.PERCENT,
        "value": "150.00",
        "recipient_email": "test@example.com",
    }
    with patch("discounts.services.campaign.send_campaign_offer_email"):
        response = admin_client.post(CAMPAIGN_URL, data)

    assert response.status_code == 200
    assert OrderPromotion.objects.count() == 0


# ---------------------------------------------------------------------------
# CampaignCreateForm standalone validation
# ---------------------------------------------------------------------------


def test_form_valid_minimal():
    """Form is valid with required fields only."""
    form = CampaignCreateForm(
        data={
            "name": "Test",
            "code": "test-code",
            "type": PromotionType.PERCENT,
            "value": "10",
            "recipient_email": "x@example.com",
        }
    )
    assert form.is_valid(), form.errors


def test_form_invalid_percent_over_100():
    """PERCENT value > 100 fails validation."""
    form = CampaignCreateForm(
        data={
            "name": "Test",
            "code": "test-code",
            "type": PromotionType.PERCENT,
            "value": "101",
            "recipient_email": "x@example.com",
        }
    )
    assert not form.is_valid()
    assert "value" in form.errors


def test_form_invalid_active_from_after_active_to():
    """active_from later than active_to fails validation."""
    form = CampaignCreateForm(
        data={
            "name": "Test",
            "code": "test-code",
            "type": PromotionType.FIXED,
            "value": "50",
            "recipient_email": "x@example.com",
            "active_from": "2026-12-01",
            "active_to": "2026-01-01",
        }
    )
    assert not form.is_valid()
    assert "active_from" in form.errors


def test_form_invalid_blank_value():
    """Zero or negative discount value fails the min_value validator."""
    form = CampaignCreateForm(
        data={
            "name": "Test",
            "code": "test-code",
            "type": PromotionType.FIXED,
            "value": "0",
            "recipient_email": "x@example.com",
        }
    )
    assert not form.is_valid()
    assert "value" in form.errors


def test_form_invalid_email():
    """Malformed email address fails validation."""
    form = CampaignCreateForm(
        data={
            "name": "Test",
            "code": "test-code",
            "type": PromotionType.PERCENT,
            "value": "10",
            "recipient_email": "not-an-email",
        }
    )
    assert not form.is_valid()
    assert "recipient_email" in form.errors
