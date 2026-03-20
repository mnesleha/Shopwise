"""Tests for Offer.status lifecycle transitions.

Phase 4 / Offer Lifecycle.

Covers:
1. Offer creation defaults to CREATED.
2. Successful campaign email send advances status to DELIVERED.
3. Failed campaign email send leaves status as CREATED.
4. Successful claim (ClaimOfferView) advances status to CLAIMED.
5. Claim on a CREATED offer (not yet delivered) also advances to CLAIMED.
6. Failed claim (bad token) does not create or mutate any Offer row.
7. Failed claim (inactive offer) does not change Offer status.
8. Claiming a REDEEMED offer does not downgrade its status.
9. Successful checkout where campaign offer is the winning discount advances to REDEEMED.
10. Checkout without a campaign offer does not change an unrelated Offer's status.
11. create_and_send_campaign_offer returns an Offer with DELIVERED status in-memory
    (no extra refresh needed by callers) when email succeeds.
12. EXPIRED offer is not transitioned to REDEEMED at checkout (forward-only guard).

EXPIRED: automatic expiration via scheduler is intentionally deferred —
the EXPIRED status value exists and can be set manually by admins, but
automatic expiration is out of scope until a scheduled-job slice is added.
"""

from decimal import Decimal
from unittest.mock import patch
import uuid

import pytest
from rest_framework.test import APIClient

from discounts.models import (
    AcquisitionMode,
    Offer,
    OfferStatus,
    OrderPromotion,
    PromotionType,
    StackingPolicy,
)
from products.models import Product, TaxClass
from tests.conftest import checkout_payload
from api.services.campaign_offer_session import CAMPAIGN_OFFER_COOKIE


CLAIM_URL = "/api/v1/cart/offer/claim/"
CART_ITEMS_URL = "/api/v1/cart/items/"
CHECKOUT_URL = "/api/v1/cart/checkout/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_code() -> str:
    """Return a short unique promotion code safe for parallel test runs."""
    return f"LC-{uuid.uuid4().hex[:10]}"


def _tax_class() -> TaxClass:
    return TaxClass.objects.create(
        name=f"Standard LC {uuid.uuid4().hex[:6]}",
        code=f"stdlc{uuid.uuid4().hex[:8]}",
        rate=Decimal("0"),  # zero rate keeps price assertions simple
    )


def _product(*, price_net: Decimal = Decimal("100.00")) -> Product:
    return Product.objects.create(
        name=f"Widget {uuid.uuid4().hex[:6]}",
        price=price_net,
        stock_quantity=100,
        is_active=True,
        price_net_amount=price_net,
        currency="EUR",
        tax_class=_tax_class(),
    )


def _campaign_promo(
    *,
    value: Decimal = Decimal("20"),
    promo_type: str = PromotionType.FIXED,
    priority: int = 5,
    minimum_order_value: Decimal | None = None,
) -> OrderPromotion:
    return OrderPromotion.objects.create(
        name="Test Campaign",
        code=_unique_code(),
        type=promo_type,
        value=value,
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=priority,
        is_active=True,
        minimum_order_value=minimum_order_value,
    )


def _offer(
    promotion: OrderPromotion,
    *,
    token: str | None = None,
    is_active: bool = True,
    status: str = OfferStatus.CREATED,
) -> Offer:
    return Offer.objects.create(
        token=token or uuid.uuid4().hex,
        promotion=promotion,
        status=status,
        is_active=is_active,
    )


# ---------------------------------------------------------------------------
# 1. Model default
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_offer_status_defaults_to_created():
    """An Offer created without an explicit status must default to CREATED."""
    promo = _campaign_promo()
    offer = Offer.objects.create(
        token=uuid.uuid4().hex,
        promotion=promo,
        is_active=True,
    )
    assert offer.status == OfferStatus.CREATED


# ---------------------------------------------------------------------------
# 2 & 3. DELIVERED via campaign service
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_campaign_service_sets_delivered_on_email_success():
    """create_and_send_campaign_offer must advance offer status to DELIVERED
    when send_campaign_offer_email returns True."""
    from discounts.services.campaign import create_and_send_campaign_offer

    with patch(
        "discounts.services.campaign.send_campaign_offer_email",
        return_value=True,
    ):
        _promo, offer, _url = create_and_send_campaign_offer(
            name="Summer 20",
            code=_unique_code(),
            type=PromotionType.FIXED,
            value=Decimal("20"),
            recipient_email="customer@example.com",
        )

    offer.refresh_from_db()
    assert offer.status == OfferStatus.DELIVERED


@pytest.mark.django_db
def test_campaign_service_keeps_created_on_email_failure():
    """create_and_send_campaign_offer must leave offer status as CREATED
    when send_campaign_offer_email returns False (delivery failed)."""
    from discounts.services.campaign import create_and_send_campaign_offer

    with patch(
        "discounts.services.campaign.send_campaign_offer_email",
        return_value=False,
    ):
        _promo, offer, _url = create_and_send_campaign_offer(
            name="Summer 20 Fail",
            code=_unique_code(),
            type=PromotionType.FIXED,
            value=Decimal("20"),
            recipient_email="customer@example.com",
        )

    offer.refresh_from_db()
    assert offer.status == OfferStatus.CREATED


# ---------------------------------------------------------------------------
# 4 & 5. CLAIMED via ClaimOfferView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_claim_view_delivered_offer_advances_to_claimed():
    """POST /claim/ with a DELIVERED offer must advance status to CLAIMED."""
    promo = _campaign_promo()
    offer = _offer(promo, status=OfferStatus.DELIVERED)
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 200
    offer.refresh_from_db()
    assert offer.status == OfferStatus.CLAIMED


@pytest.mark.django_db
def test_claim_view_created_offer_advances_to_claimed():
    """POST /claim/ on a CREATED offer (email may not have been sent yet) must
    also advance status to CLAIMED."""
    promo = _campaign_promo()
    offer = _offer(promo, status=OfferStatus.CREATED)
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 200
    offer.refresh_from_db()
    assert offer.status == OfferStatus.CLAIMED


# ---------------------------------------------------------------------------
# 6. Failed claim — bad token
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_claim_view_bad_token_does_not_mutate_any_offer():
    """A 404 claim (non-existent token) must not create or alter any Offer row."""
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": "this-token-does-not-exist"}, format="json")

    assert resp.status_code == 404
    assert not Offer.objects.filter(token="this-token-does-not-exist").exists()


# ---------------------------------------------------------------------------
# 7. Failed claim — inactive offer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_claim_view_inactive_offer_does_not_advance_status():
    """A 400 claim on an inactive offer must not change the offer status."""
    promo = _campaign_promo()
    offer = _offer(promo, is_active=False, status=OfferStatus.CREATED)
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 400
    offer.refresh_from_db()
    assert offer.status == OfferStatus.CREATED


# ---------------------------------------------------------------------------
# 8. Already-REDEEMED offer is not downgraded by a re-claim
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_claim_view_does_not_downgrade_redeemed_offer():
    """Claiming an already-REDEEMED offer must not downgrade its status back to CLAIMED."""
    promo = _campaign_promo()
    offer = _offer(promo, status=OfferStatus.REDEEMED)
    client = APIClient()

    # The claim endpoint succeeds (200) because is_currently_active() only
    # checks is_active and date window — not the lifecycle status field.
    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 200
    offer.refresh_from_db()
    # The conditional filter (status__in=[CREATED, DELIVERED]) did not match REDEEMED,
    # so the status must remain REDEEMED.
    assert offer.status == OfferStatus.REDEEMED


# ---------------------------------------------------------------------------
# 9. REDEEMED via CartCheckoutView (campaign offer is the winning discount)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_checkout_advances_offer_to_redeemed_when_campaign_offer_wins():
    """Successful checkout where the campaign offer is the winning discount
    must advance the Offer status to REDEEMED."""
    # Use a high-priority FIXED-20 offer against a €100 product so it wins.
    promo = _campaign_promo(
        value=Decimal("20"),
        promo_type=PromotionType.FIXED,
        priority=99,
    )
    offer = _offer(promo, status=OfferStatus.CLAIMED)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    client.post(CART_ITEMS_URL, {"product_id": product.id, "quantity": 1}, format="json")
    # Inject the campaign offer cookie so checkout picks it up.
    client.cookies[CAMPAIGN_OFFER_COOKIE] = offer.token

    resp = client.post(CHECKOUT_URL, checkout_payload(), format="json")

    assert resp.status_code == 201, resp.json()
    offer.refresh_from_db()
    assert offer.status == OfferStatus.REDEEMED


# ---------------------------------------------------------------------------
# 10. Checkout without a campaign offer does not change unrelated offer status
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_checkout_without_campaign_offer_does_not_change_offer_status():
    """An offer not present in the checkout session must be untouched after
    a successful checkout."""
    promo = _campaign_promo()
    offer = _offer(promo, status=OfferStatus.DELIVERED)
    product = _product(price_net=Decimal("50.00"))

    client = APIClient()
    client.post(CART_ITEMS_URL, {"product_id": product.id, "quantity": 1}, format="json")
    # No campaign offer cookie injected.

    resp = client.post(CHECKOUT_URL, checkout_payload(), format="json")

    assert resp.status_code == 201, resp.json()
    offer.refresh_from_db()
    assert offer.status == OfferStatus.DELIVERED  # must remain unchanged


# ---------------------------------------------------------------------------
# 11. In-memory Offer.status consistency after service call (Fix 3)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_campaign_service_offer_status_is_delivered_in_memory_after_success():
    """create_and_send_campaign_offer must return an Offer whose .status is
    already DELIVERED when email sending succeeded — callers must not need to
    refresh_from_db to read the correct lifecycle state."""
    from discounts.services.campaign import create_and_send_campaign_offer

    with patch(
        "discounts.services.campaign.send_campaign_offer_email",
        return_value=True,
    ):
        _promo, offer, _url = create_and_send_campaign_offer(
            name="In-Memory Check",
            code=_unique_code(),
            type=PromotionType.FIXED,
            value=Decimal("10"),
            recipient_email="check@example.com",
        )

    # In-memory instance must already be consistent — no refresh required.
    assert offer.status == OfferStatus.DELIVERED


@pytest.mark.django_db
def test_campaign_service_offer_status_remains_created_in_memory_on_failure():
    """When email delivery fails the returned Offer's in-memory status is
    CREATED (not falsely DELIVERED)."""
    from discounts.services.campaign import create_and_send_campaign_offer

    with patch(
        "discounts.services.campaign.send_campaign_offer_email",
        return_value=False,
    ):
        _promo, offer, _url = create_and_send_campaign_offer(
            name="In-Memory Fail",
            code=_unique_code(),
            type=PromotionType.FIXED,
            value=Decimal("10"),
            recipient_email="check@example.com",
        )

    assert offer.status == OfferStatus.CREATED


# ---------------------------------------------------------------------------
# 12. EXPIRED offer is not overwritten by REDEEMED at checkout (Fix 4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_checkout_does_not_transition_expired_offer_to_redeemed():
    """An EXPIRED offer present in the checkout session must not be
    transitioned to REDEEMED — the forward-only guard must block it."""
    promo = _campaign_promo(
        value=Decimal("20"),
        promo_type=PromotionType.FIXED,
        priority=99,
    )
    offer = _offer(promo, status=OfferStatus.EXPIRED)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    client.post(CART_ITEMS_URL, {"product_id": product.id, "quantity": 1}, format="json")
    # Inject the expired offer cookie so checkout attempts to use it.
    client.cookies[CAMPAIGN_OFFER_COOKIE] = offer.token

    resp = client.post(CHECKOUT_URL, checkout_payload(), format="json")

    # Checkout request itself succeeds (the view reads pricing from the cookie
    # but the status update is filtered; the promotion discount may or may not
    # apply depending on is_currently_active — that's orthogonal).
    # The important assertion is that status was not overwritten.
    offer.refresh_from_db()
    assert offer.status == OfferStatus.EXPIRED, (
        f"Expected EXPIRED, got {offer.status} — forward-only guard failed"
    )
