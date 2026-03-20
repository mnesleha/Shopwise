"""Thin service for the campaign creation admin flow.

Phase 4 / Admin Slice 2.

Keeps the view layer free of domain logic and makes the core operation
testable in isolation.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction

from notifications.jobs import send_campaign_offer_email

from ..models import AcquisitionMode, Offer, OfferStatus, OrderPromotion, StackingPolicy

if TYPE_CHECKING:
    import datetime
    from decimal import Decimal


def create_and_send_campaign_offer(
    *,
    name: str,
    code: str,
    type: str,
    value: "Decimal",
    recipient_email: str,
    minimum_order_value: "Decimal | None" = None,
    is_discoverable: bool = False,
    active_from: "datetime.date | None" = None,
    active_to: "datetime.date | None" = None,
    offer_active_to: "datetime.date | None" = None,
) -> tuple["OrderPromotion", "Offer", str]:
    """Create a CAMPAIGN_APPLY promotion, a linked Offer, and send the claim email.

    This is the single entry-point for the guided campaign creation admin flow.
    Offer token generation and URL construction are handled here so that the
    merchant-facing view never needs to know about them.

    The promotion and offer are created inside a transaction so a DB failure
    rolls both back cleanly.  Email sending is intentionally outside the
    transaction — it is best-effort and non-transactional.

    Args:
        name: Human-readable promotion name.
        code: Machine-readable promotion code (must be unique).
        type: PromotionType value — PERCENT or FIXED.
        value: Discount magnitude.
        recipient_email: Delivery address for the claim link.
        minimum_order_value: Optional cart total threshold for eligibility.
        is_discoverable: Whether the promotion is surfaced in storefront messaging.
        active_from: Optional promotion start date.
        active_to: Optional promotion end date.
        offer_active_to: Optional expiry date for the offer token specifically.

    Returns:
        A 3-tuple of (promotion, offer, claim_url).
    """
    with transaction.atomic():
        promotion = OrderPromotion.objects.create(
            name=name,
            code=code,
            type=type,
            value=value,
            acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
            stacking_policy=StackingPolicy.EXCLUSIVE,
            minimum_order_value=minimum_order_value,
            is_discoverable=is_discoverable,
            active_from=active_from,
            active_to=active_to,
            is_active=True,
        )

        token = uuid.uuid4().hex  # 32 lowercase hex characters, globally unique
        offer = Offer.objects.create(
            promotion=promotion,
            token=token,
            is_active=True,
            active_to=offer_active_to,
        )

    claim_url = f"{settings.PUBLIC_BASE_URL}/claim-offer?token={token}"

    # Intentionally outside the transaction — best-effort, failures do not
    # roll back the already-committed promotion / offer rows.
    # The return value tells us whether delivery succeeded so we can advance
    # the offer lifecycle from CREATED → DELIVERED.
    delivered = send_campaign_offer_email(
        recipient_email=recipient_email,
        offer_url=claim_url,
        promotion_name=promotion.name,
    )
    if delivered:
        # Only advance forward; never overwrite CLAIMED / REDEEMED.
        Offer.objects.filter(
            pk=offer.pk, status=OfferStatus.CREATED
        ).update(status=OfferStatus.DELIVERED)
        # Keep the in-memory instance consistent with the DB row so callers
        # can read offer.status without an extra DB round-trip.
        offer.status = OfferStatus.DELIVERED

    return promotion, offer, claim_url
