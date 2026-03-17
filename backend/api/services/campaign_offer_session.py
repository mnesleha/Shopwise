"""Cookie helpers for the campaign offer claim/apply flow.

Phase 4 / Slice 5B.

The claimed offer token is stored in a dedicated HttpOnly cookie
(``campaign_offer_token``) rather than the Django session.  Cookie-based
storage is resilient to ``SESSION_COOKIE_SECURE = True`` in HTTP development
environments, and works identically for anonymous and authenticated users —
mirroring the existing ``cart_token`` cookie pattern.

This module is intentionally free of Django views imports so that both
``api/views/carts.py`` and ``api/serializers/cart.py`` can import it without
causing a circular dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from discounts.models import Offer


#: Name of the cookie that carries the claimed campaign offer token.
CAMPAIGN_OFFER_COOKIE = "campaign_offer_token"


def _cookie_kwargs() -> dict:
    return {
        "httponly": True,
        "samesite": "Lax",
        # Secure only when explicitly configured *or* when DEBUG is False.
        # In local HTTP dev (DEBUG=True) this defaults to False so the browser
        # accepts the cookie without HTTPS.
        "secure": getattr(
            settings, "CAMPAIGN_OFFER_COOKIE_SECURE", not settings.DEBUG
        ),
        "path": "/",
    }


def get_claimed_campaign_offer(request) -> "Offer | None":
    """Resolve a claimed campaign offer from the request cookie.

    Reads ``request.COOKIES["campaign_offer_token"]`` and returns the
    corresponding ``Offer`` when it exists, is currently active, and belongs
    to a ``CAMPAIGN_APPLY`` promotion.

    Returns ``None`` when:
    - *request* is ``None`` (serializer called without request context)
    - the cookie is absent or empty
    - the token does not exist in the database
    - the offer is inactive or outside its date window
    - the promotion is not ``CAMPAIGN_APPLY``
    """
    if request is None:
        return None

    token = request.COOKIES.get(CAMPAIGN_OFFER_COOKIE, "").strip()
    if not token:
        return None

    # Lazy import to keep this module free of top-level app dependencies.
    from discounts.models import AcquisitionMode, Offer  # noqa: PLC0415

    try:
        offer = Offer.objects.select_related("promotion").get(token=token)
    except Offer.DoesNotExist:
        return None

    if (
        not offer.is_currently_active()
        or offer.promotion.acquisition_mode != AcquisitionMode.CAMPAIGN_APPLY
    ):
        return None

    return offer


def set_campaign_offer_cookie(response, token: str) -> None:
    """Set the ``campaign_offer_token`` cookie on an outgoing DRF/Django response.

    Called by ``ClaimOfferView.post()`` after a successful token validation.
    """
    response.set_cookie(CAMPAIGN_OFFER_COOKIE, token, **_cookie_kwargs())


def clear_campaign_offer_cookie(response) -> None:
    """Delete the ``campaign_offer_token`` cookie on an outgoing response.

    Called by ``CartCheckoutView.post()`` after a successful checkout so the
    same offer is not silently re-applied to the next order.
    """
    response.delete_cookie(CAMPAIGN_OFFER_COOKIE, path="/")
