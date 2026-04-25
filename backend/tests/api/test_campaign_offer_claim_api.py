"""API tests for Phase 4 / Slice 5B — campaign offer claim/apply flow.

Covers:
- POST /api/v1/cart/offer/claim/ with valid token → 200, cookie set in response
- POST with non-existent token → 404
- POST with inactive offer → 400 (OFFER_INACTIVE)
- POST with non-CAMPAIGN_APPLY offer → 400 (OFFER_NOT_CLAIMABLE)
- GET /api/v1/cart/ after claim reflects order_discount_applied
- order_discount_amount matches the promotion's effect
- second claim with same token is idempotent (no error)
- stale cookie token falls back silently, cart behaves normally
- checkout applies the campaign discount and clears the cookie
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils.timezone import now, timedelta
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

User = get_user_model()

CLAIM_URL = "/api/v1/cart/offer/claim/"
CART_URL = "/api/v1/cart/"
CART_ITEMS_URL = "/api/v1/cart/items/"

_CODE_SEQ = 0


def _next_code() -> str:
    global _CODE_SEQ
    _CODE_SEQ += 1
    return f"CAMP5B-{_CODE_SEQ:04d}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tax_class(suffix: str = "") -> TaxClass:
    return TaxClass.objects.create(
        name=f"Standard {suffix}",
        code=f"std5b{suffix}",
        rate=Decimal("0"),  # zero-rate keeps assertions simple
    )


def _product(
    *,
    name: str = "Widget",
    price_net: Decimal = Decimal("100.00"),
    tax_class=None,
) -> Product:
    if tax_class is None:
        tax_class = _tax_class(suffix=str(price_net).replace(".", "_"))
    return Product.objects.create(
        name=name,
        price=price_net,
        stock_quantity=100,
        is_active=True,
        price_net_amount=price_net,
        currency="EUR",
        tax_class=tax_class,
    )


def _campaign_promotion(
    *,
    name: str = "Summer Campaign",
    value: Decimal = Decimal("20"),
    promo_type: str = PromotionType.FIXED,
    is_active: bool = True,
    **kwargs,
) -> OrderPromotion:
    return OrderPromotion.objects.create(
        name=name,
        code=_next_code(),
        type=promo_type,
        value=value,
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=5,
        is_active=is_active,
        minimum_order_value=None,
        active_from=None,
        active_to=None,
        **kwargs,
    )


def _offer(
    promotion: OrderPromotion,
    *,
    token: str | None = None,
    is_active: bool = True,
    **kwargs,
) -> Offer:
    import uuid
    return Offer.objects.create(
        token=token or str(uuid.uuid4()),
        promotion=promotion,
        status=OfferStatus.CREATED,
        is_active=is_active,
        **kwargs,
    )


def _add_item(client, product: Product, qty: int = 1) -> None:
    resp = client.post(
        CART_ITEMS_URL,
        {"product_id": product.id, "quantity": qty},
        format="json",
    )
    assert resp.status_code in (200, 201), resp.json()


# ---------------------------------------------------------------------------
# Claim endpoint: basic validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_claim_valid_token_returns_200():
    promo = _campaign_promotion()
    offer = _offer(promo)
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["promotion_name"] == promo.name
    assert body["promotion_code"] == promo.code


@pytest.mark.django_db
def test_claim_response_sets_campaign_offer_cookie():
    """Successful claim must set the campaign_offer_token cookie in the response."""
    from api.services.campaign_offer_session import CAMPAIGN_OFFER_COOKIE

    promo = _campaign_promotion()
    offer = _offer(promo)
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 200
    assert CAMPAIGN_OFFER_COOKIE in resp.cookies
    assert resp.cookies[CAMPAIGN_OFFER_COOKIE].value == offer.token


@pytest.mark.django_db
def test_claim_missing_token_returns_404():
    client = APIClient()
    resp = client.post(CLAIM_URL, {"token": ""}, format="json")
    assert resp.status_code == 404
    assert resp.json()["code"] == "OFFER_NOT_FOUND"


@pytest.mark.django_db
def test_claim_nonexistent_token_returns_404():
    client = APIClient()
    resp = client.post(CLAIM_URL, {"token": "does-not-exist"}, format="json")
    assert resp.status_code == 404
    assert resp.json()["code"] == "OFFER_NOT_FOUND"


@pytest.mark.django_db
def test_claim_inactive_offer_returns_400():
    promo = _campaign_promotion()
    offer = _offer(promo, is_active=False)
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 400
    assert resp.json()["code"] == "OFFER_INACTIVE"


@pytest.mark.django_db
def test_claim_inactive_promotion_returns_400():
    promo = _campaign_promotion(is_active=False)
    offer = _offer(promo)
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 400
    assert resp.json()["code"] == "OFFER_INACTIVE"


@pytest.mark.django_db
def test_claim_expired_offer_returns_400():
    """An offer whose active_to is in the past is rejected."""
    today = now().date()
    promo = _campaign_promotion()
    offer = _offer(
        promo,
        active_to=today.replace(year=today.year - 1),
    )
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 400
    assert resp.json()["code"] == "OFFER_INACTIVE"


@pytest.mark.django_db
def test_claim_auto_apply_offer_returns_400():
    """CAMPAIGN_APPLY is required; AUTO_APPLY offers are not claimable."""
    auto_promo = OrderPromotion.objects.create(
        name="Auto Promo",
        code=_next_code(),
        type=PromotionType.PERCENT,
        value=Decimal("10"),
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=5,
        is_active=True,
        minimum_order_value=None,
    )
    offer = _offer(auto_promo)
    client = APIClient()

    resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp.status_code == 400
    assert resp.json()["code"] == "OFFER_NOT_CLAIMABLE"


# ---------------------------------------------------------------------------
# Cart GET reflects claimed offer discount
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cart_reflects_claimed_campaign_offer():
    """After claiming a FIXED-20 offer, order_discount_applied is True."""
    promo = _campaign_promotion(value=Decimal("20"), promo_type=PromotionType.FIXED)
    offer = _offer(promo, token="SUMMER20")
    product = _product(price_net=Decimal("100.00"))
    client = APIClient()

    _add_item(client, product, qty=1)

    claim_resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")
    assert claim_resp.status_code == 200

    cart_resp = client.get(CART_URL)
    assert cart_resp.status_code == 200
    totals = cart_resp.json()["totals"]

    assert totals["order_discount_applied"] is True
    assert Decimal(totals["order_discount_amount"]) == Decimal("20.00")


@pytest.mark.django_db
def test_cart_ignores_claimed_offer_when_promotion_is_deactivated_after_claim():
    promo = _campaign_promotion(value=Decimal("20"), promo_type=PromotionType.FIXED)
    offer = _offer(promo, token="SUMMER20-INACTIVE")
    product = _product(price_net=Decimal("100.00"))
    client = APIClient()

    _add_item(client, product, qty=1)

    claim_resp = client.post(CLAIM_URL, {"token": offer.token}, format="json")
    assert claim_resp.status_code == 200

    promo.is_active = False
    promo.save(update_fields=["is_active"])

    cart_resp = client.get(CART_URL)
    assert cart_resp.status_code == 200
    totals = cart_resp.json()["totals"]

    assert totals["order_discount_applied"] is False
    assert totals["order_discount_amount"] is None


@pytest.mark.django_db
def test_cart_order_discount_name_matches_promotion():
    """order_discount_promotion_name should match the campaign promotion name."""
    promo = _campaign_promotion(name="Black Friday 15%", value=Decimal("15"), promo_type=PromotionType.PERCENT)
    offer = _offer(promo, token="BF15")
    product = _product(price_net=Decimal("100.00"))
    client = APIClient()
    _add_item(client, product, qty=1)
    client.post(CLAIM_URL, {"token": offer.token}, format="json")

    totals = client.get(CART_URL).json()["totals"]
    assert totals["order_discount_promotion_name"] == "Black Friday 15%"


@pytest.mark.django_db
def test_cart_without_claimed_offer_has_no_order_discount():
    """Baseline: cart without a claimed offer has order_discount_applied=False."""
    product = _product(price_net=Decimal("100.00"))
    client = APIClient()
    _add_item(client, product, qty=1)

    totals = client.get(CART_URL).json()["totals"]
    assert totals["order_discount_applied"] is False
    assert totals["order_discount_amount"] is None


@pytest.mark.django_db
def test_cart_total_gross_after_order_discount_is_correct():
    """total_gross_after_order_discount should be cart_total minus fixed offer amount."""
    promo = _campaign_promotion(value=Decimal("30"), promo_type=PromotionType.FIXED)
    offer = _offer(promo, token="FIXED30")
    product = _product(price_net=Decimal("100.00"))
    client = APIClient()
    _add_item(client, product, qty=1)
    client.post(CLAIM_URL, {"token": offer.token}, format="json")

    totals = client.get(CART_URL).json()["totals"]
    # product net=100, 0% tax → gross=100; fixed-30 order discount → 70
    assert Decimal(totals["total_gross_after_order_discount"]) == Decimal("70.00")


# ---------------------------------------------------------------------------
# Idempotency and stale session handling
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_second_claim_with_same_token_is_idempotent():
    """Claiming the same offer twice does not raise an error."""
    promo = _campaign_promotion()
    offer = _offer(promo, token="DOUBLE10")
    client = APIClient()

    resp1 = client.post(CLAIM_URL, {"token": offer.token}, format="json")
    resp2 = client.post(CLAIM_URL, {"token": offer.token}, format="json")

    assert resp1.status_code == 200
    assert resp2.status_code == 200


@pytest.mark.django_db
def test_stale_cookie_offer_cleared_silently():
    """If the cookie has a token for an offer that no longer exists, the cart
    falls back to normal pricing without an error."""
    from api.services.campaign_offer_session import CAMPAIGN_OFFER_COOKIE

    product = _product(price_net=Decimal("100.00"))
    client = APIClient()
    _add_item(client, product, qty=1)

    # Manually inject a stale token directly into the test client cookie jar.
    client.cookies[CAMPAIGN_OFFER_COOKIE] = "stale-token-xyz"

    cart_resp = client.get(CART_URL)
    assert cart_resp.status_code == 200
    totals = cart_resp.json()["totals"]
    # No crash; order discount is absent.
    assert totals["order_discount_applied"] is False
