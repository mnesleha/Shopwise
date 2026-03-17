"""Unit tests for Phase 4 / Slice 5A — campaign offer email.

Covers:
- render_campaign_offer_email: subject/body contain offer_url and promotion_name
- send_campaign_offer_email job: sends via locmem, correct recipient, contains token URL
- send_campaign_offer_email job: swallows exceptions (best-effort semantics)
- Admin action: rejects multiple selected offers
- Admin action: rejects non-CAMPAIGN_APPLY promotion
- Admin action: renders intermediate form for a valid single offer
- Admin action: sends email on confirm POST and shows success message
- Admin action: sent email body contains /claim-offer?token=...
"""

import pytest
from unittest.mock import patch

from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.test import RequestFactory, override_settings

from discounts.admin import OfferAdmin
from discounts.models import AcquisitionMode, Offer, OrderPromotion, PromotionType, StackingPolicy
from notifications.renderers import render_campaign_offer_email
from notifications import jobs

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CODE_SEQ = 0


def _next_code() -> str:
    global _CODE_SEQ
    _CODE_SEQ += 1
    return f"CAMP-{_CODE_SEQ:04d}"


def make_campaign_promotion(**kwargs) -> OrderPromotion:
    defaults = dict(
        code=_next_code(),
        name="Summer Campaign",
        type=PromotionType.FIXED,
        value=20,
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=5,
        is_active=True,
        minimum_order_value=None,
        active_from=None,
        active_to=None,
    )
    defaults.update(kwargs)
    return OrderPromotion.objects.create(**defaults)


def make_offer(promotion: OrderPromotion, **kwargs) -> Offer:
    import uuid
    defaults = dict(
        token=str(uuid.uuid4()),
        promotion=promotion,
        status="active",
        is_active=True,
    )
    defaults.update(kwargs)
    return Offer.objects.create(**defaults)


def _request_with_messages(method="post", data=None):
    """Return a RequestFactory request wired up with messages middleware."""
    factory = RequestFactory()
    if method == "post":
        request = factory.post("/admin/discounts/offer/", data=data or {})
    else:
        request = factory.get("/admin/discounts/offer/")
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


# ---------------------------------------------------------------------------
# render_campaign_offer_email
# ---------------------------------------------------------------------------

def test_render_campaign_offer_email_subject_contains_promotion_name():
    subject, _ = render_campaign_offer_email(
        recipient_email="alice@example.com",
        offer_url="https://shop.test/claim-offer?token=tok_abc",
        promotion_name="Summer Sale",
    )
    assert "Summer Sale" in subject


def test_render_campaign_offer_email_body_contains_offer_url():
    _, body = render_campaign_offer_email(
        recipient_email="alice@example.com",
        offer_url="https://shop.test/claim-offer?token=tok_abc",
        promotion_name="Summer Sale",
    )
    assert "https://shop.test/claim-offer?token=tok_abc" in body


def test_render_campaign_offer_email_body_contains_promotion_name():
    _, body = render_campaign_offer_email(
        recipient_email="alice@example.com",
        offer_url="https://shop.test/claim-offer?token=tok_abc",
        promotion_name="Summer Sale",
    )
    assert "Summer Sale" in body


def test_render_campaign_offer_email_returns_nonempty_strings():
    subject, body = render_campaign_offer_email(
        recipient_email="alice@example.com",
        offer_url="https://shop.test/claim-offer?token=tok_abc",
        promotion_name="Summer Sale",
    )
    assert isinstance(subject, str) and subject.strip()
    assert isinstance(body, str) and body.strip()


# ---------------------------------------------------------------------------
# send_campaign_offer_email job
# ---------------------------------------------------------------------------

@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
def test_send_campaign_offer_email_sends_one_email():
    mail.outbox.clear()
    jobs.send_campaign_offer_email(
        recipient_email="bob@example.com",
        offer_url="https://shop.test/claim-offer?token=tok_xyz",
        promotion_name="Flash Deal",
    )
    assert len(mail.outbox) == 1


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
def test_send_campaign_offer_email_to_correct_recipient():
    mail.outbox.clear()
    jobs.send_campaign_offer_email(
        recipient_email="bob@example.com",
        offer_url="https://shop.test/claim-offer?token=tok_xyz",
        promotion_name="Flash Deal",
    )
    assert mail.outbox[0].to == ["bob@example.com"]


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
def test_send_campaign_offer_email_body_contains_token_url():
    mail.outbox.clear()
    jobs.send_campaign_offer_email(
        recipient_email="bob@example.com",
        offer_url="https://shop.test/claim-offer?token=tok_xyz",
        promotion_name="Flash Deal",
    )
    assert "tok_xyz" in mail.outbox[0].body


def test_send_campaign_offer_email_swallows_exceptions():
    """Best-effort: failures must not propagate to the caller."""
    with patch("notifications.jobs.EmailService.send_plain_text", side_effect=Exception("SMTP down")):
        # Must not raise
        jobs.send_campaign_offer_email(
            recipient_email="carol@example.com",
            offer_url="https://shop.test/claim-offer?token=tok_fail",
            promotion_name="Broken Deal",
        )


# ---------------------------------------------------------------------------
# Admin action
# ---------------------------------------------------------------------------

@pytest.fixture()
def offer_admin():
    site = AdminSite()
    return OfferAdmin(Offer, site)


def test_admin_action_rejects_multiple_offers(offer_admin):
    promo = make_campaign_promotion()
    offer1 = make_offer(promo)
    offer2 = make_offer(promo)
    qs = Offer.objects.filter(pk__in=[offer1.pk, offer2.pk])

    request = _request_with_messages()
    offer_admin.send_offer_email(request, qs)

    stored = list(messages.get_messages(request))
    assert any("exactly one" in str(m).lower() for m in stored)


def test_admin_action_rejects_non_campaign_apply_offer(offer_admin):
    promo = OrderPromotion.objects.create(
        code=_next_code(),
        name="Manual Promo",
        type=PromotionType.FIXED,
        value=10,
        acquisition_mode=AcquisitionMode.MANUAL_ENTRY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=5,
        is_active=True,
        minimum_order_value=None,
        active_from=None,
        active_to=None,
    )
    offer = make_offer(promo)
    qs = Offer.objects.filter(pk=offer.pk)

    request = _request_with_messages()
    offer_admin.send_offer_email(request, qs)

    stored = list(messages.get_messages(request))
    assert any("campaign_apply" in str(m).lower() for m in stored)


@override_settings(
    PUBLIC_BASE_URL="https://shop.test",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
def test_admin_action_shows_intermediate_form(offer_admin):
    promo = make_campaign_promotion(name="Spring Offer")
    offer = make_offer(promo)
    qs = Offer.objects.filter(pk=offer.pk)

    factory = RequestFactory()
    request = factory.post("/admin/discounts/offer/", data={
        "action": "send_offer_email",
        "_selected_action": str(offer.pk),
    })
    request.session = {}
    request._messages = FallbackStorage(request)

    response = offer_admin.send_offer_email(request, qs)

    # Should return a TemplateResponse (step 1 form), not None
    assert response is not None
    assert response.status_code == 200
    assert "offer" in response.context_data
    assert response.context_data["offer"].pk == offer.pk


@override_settings(
    PUBLIC_BASE_URL="https://shop.test",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
def test_admin_action_sends_email_on_confirm(offer_admin):
    mail.outbox.clear()
    promo = make_campaign_promotion(name="Exclusive Offer")
    offer = make_offer(promo)
    qs = Offer.objects.filter(pk=offer.pk)

    request = _request_with_messages(data={
        "action": "send_offer_email",
        "_selected_action": str(offer.pk),
        "confirm": "1",
        "recipient_email": "dave@example.com",
    })

    offer_admin.send_offer_email(request, qs)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["dave@example.com"]


@override_settings(
    PUBLIC_BASE_URL="https://shop.test",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
def test_admin_action_email_contains_offer_token(offer_admin):
    mail.outbox.clear()
    promo = make_campaign_promotion(name="Token Check Offer")
    offer = make_offer(promo)
    qs = Offer.objects.filter(pk=offer.pk)

    request = _request_with_messages(data={
        "action": "send_offer_email",
        "_selected_action": str(offer.pk),
        "confirm": "1",
        "recipient_email": "eve@example.com",
    })

    offer_admin.send_offer_email(request, qs)

    assert len(mail.outbox) == 1
    assert f"/claim-offer?token={offer.token}" in mail.outbox[0].body
