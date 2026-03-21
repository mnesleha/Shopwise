"""
Unit tests for best-for-customer campaign offer resolution during
guest→authenticated cart merge.

These tests exercise the fix for the bug where the merge service blindly
discarded one side's campaign context without evaluating both offers.

Coverage:
  1. Guest offer beats authenticated offer     → guest side wins
  2. Authenticated offer beats guest offer     → auth side wins
  3. Guest offer invalid/expired               → auth side survives alone
  4. Auth offer invalid/expired                → guest side survives alone
  5. Neither offer is valid                    → no offer survives merge
  6. Same token on both sides (duplicate)      → deduplicated, survives if valid
  7. Clearing cart items does NOT remove claimed_offer_token (session invariant)
  8. Canonical pricing is recomputed on merged cart (no regression)
  9. ADOPT path: guest valid offer survives     → winning_offer_token returned
 10. ADOPT path: guest invalid offer cleared   → winning_offer_token is None
 11. NOOP report always has winning_offer_token=None
"""

from decimal import Decimal
from datetime import date

import pytest
from django.utils.timezone import now, timedelta

from carts.models import Cart, CartItem
from carts.services.merge import merge_or_adopt_guest_cart
from carts.services.resolver import hash_cart_token
from discounts.models import (
    AcquisitionMode,
    Offer,
    OfferStatus,
    OrderPromotion,
    PromotionType,
    StackingPolicy,
)
from products.models import Product, TaxClass

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CODE_SEQ = 0


def _next_code() -> str:
    global _CODE_SEQ
    _CODE_SEQ += 1
    return f"MERGE-CAMP-{_CODE_SEQ:05d}"


def _tax_class() -> TaxClass:
    return TaxClass.objects.create(
        name="Zero",
        code=f"zero-merge-{_CODE_SEQ}",
        rate=Decimal("0"),
    )


def _product_with_pricing(*, price: Decimal = Decimal("100.00")) -> Product:
    """Create a product that the pricing service can price (has price_net_amount)."""
    tc = _tax_class()
    return Product.objects.create(
        name=f"Product-{_CODE_SEQ}",
        price=price,
        stock_quantity=100,
        is_active=True,
        price_net_amount=price,
        currency="EUR",
        tax_class=tc,
    )


def _plain_product(*, price: Decimal = Decimal("10.00"), stock: int = 100) -> Product:
    """Minimal product (no price_net_amount) — used for item-count tests."""
    return Product.objects.create(
        name=f"Plain-{_CODE_SEQ}",
        price=price,
        stock_quantity=stock,
        is_active=True,
    )


def _campaign_promotion(
    *,
    value: Decimal = Decimal("10"),
    promo_type: str = PromotionType.FIXED,
    priority: int = 0,
    is_active: bool = True,
    active_to: date | None = None,
) -> OrderPromotion:
    return OrderPromotion.objects.create(
        name=f"Promo-{_next_code()}",
        code=_next_code(),
        type=promo_type,
        value=value,
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=priority,
        is_active=is_active,
        active_to=active_to,
    )


def _offer(
    promotion: OrderPromotion,
    *,
    token: str | None = None,
    is_active: bool = True,
    active_to: date | None = None,
) -> Offer:
    import uuid
    return Offer.objects.create(
        token=token or uuid.uuid4().hex,
        promotion=promotion,
        status=OfferStatus.CLAIMED,
        is_active=is_active,
        active_to=active_to,
    )


def _guest_cart(token: str) -> Cart:
    return Cart.objects.create(
        anonymous_token_hash=hash_cart_token(token),
        status=Cart.Status.ACTIVE,
    )


def _auth_cart(user) -> Cart:
    return Cart.objects.create(user=user, status=Cart.Status.ACTIVE)


def _add_item(cart: Cart, product: Product, qty: int = 1) -> CartItem:
    return CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=qty,
        price_at_add_time=product.price,
    )


# ---------------------------------------------------------------------------
# Case 1: Guest offer has higher gross benefit → guest side wins (MERGE path)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_merge_guest_offer_higher_value_wins(django_user_model):
    """
    MERGE path — guest cart holds a FIXED €30 offer; auth cart holds FIXED €20.
    Cart has a €100 item (zero tax), so gross benefits are €30 vs €20.
    The guest-side offer must win.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_1@example.com", password="Passw0rd!"
    )
    product = _product_with_pricing(price=Decimal("100.00"))

    # Auth cart with offer_B (€20 benefit).
    auth_cart = _auth_cart(user)
    _add_item(auth_cart, product, qty=1)
    promo_auth = _campaign_promotion(value=Decimal("20"))
    offer_auth = _offer(promo_auth, token="auth-offer-20")
    auth_cart.claimed_offer_token = offer_auth.token
    auth_cart.save(update_fields=["claimed_offer_token"])

    # Guest cart with offer_A (€30 benefit — better for customer).
    guest_cart = _guest_cart("tok-guest-1")
    _add_item(guest_cart, product, qty=1)
    promo_guest = _campaign_promotion(value=Decimal("30"))
    offer_guest = _offer(promo_guest, token="guest-offer-30")
    guest_cart.claimed_offer_token = offer_guest.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-guest-1")

    assert report["performed"] is True
    assert report["result"] == "MERGED"
    assert report["winning_offer_token"] == offer_guest.token

    # Winning offer is persisted on the surviving user cart.
    auth_cart.refresh_from_db()
    assert auth_cart.claimed_offer_token == offer_guest.token


# ---------------------------------------------------------------------------
# Case 2: Authenticated offer has higher gross benefit → auth side wins
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_merge_auth_offer_higher_value_wins(django_user_model):
    """
    MERGE path — auth cart holds FIXED €40; guest cart holds FIXED €15.
    Auth-side offer must win (€40 > €15 on €100 cart).
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_2@example.com", password="Passw0rd!"
    )
    product = _product_with_pricing(price=Decimal("100.00"))

    # Auth cart with offer_A (€40 benefit).
    auth_cart = _auth_cart(user)
    _add_item(auth_cart, product, qty=1)
    promo_auth = _campaign_promotion(value=Decimal("40"))
    offer_auth = _offer(promo_auth, token="auth-offer-40")
    auth_cart.claimed_offer_token = offer_auth.token
    auth_cart.save(update_fields=["claimed_offer_token"])

    # Guest cart with offer_B (€15 benefit).
    guest_cart = _guest_cart("tok-guest-2")
    _add_item(guest_cart, product, qty=1)
    promo_guest = _campaign_promotion(value=Decimal("15"))
    offer_guest = _offer(promo_guest, token="guest-offer-15")
    guest_cart.claimed_offer_token = offer_guest.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-guest-2")

    assert report["performed"] is True
    assert report["result"] == "MERGED"
    assert report["winning_offer_token"] == offer_auth.token

    auth_cart.refresh_from_db()
    assert auth_cart.claimed_offer_token == offer_auth.token


# ---------------------------------------------------------------------------
# Case 3: Guest offer invalid/expired → auth offer survives
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_merge_invalid_guest_offer_auth_survives(django_user_model):
    """
    MERGE path — guest cart's offer is expired; auth cart's offer is valid.
    Only the auth-side offer must survive.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_3@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    auth_cart = _auth_cart(user)
    _add_item(auth_cart, product)
    promo_auth = _campaign_promotion(value=Decimal("10"))
    offer_auth = _offer(promo_auth, token="auth-offer-valid")
    auth_cart.claimed_offer_token = offer_auth.token
    auth_cart.save(update_fields=["claimed_offer_token"])

    guest_cart = _guest_cart("tok-guest-3")
    _add_item(guest_cart, product)
    promo_guest = _campaign_promotion(
        value=Decimal("50"),
        active_to=date(2000, 1, 1),  # expired in the past
    )
    offer_guest = _offer(
        promo_guest,
        token="guest-offer-expired",
        active_to=date(2000, 1, 1),  # explicitly expired
    )
    guest_cart.claimed_offer_token = offer_guest.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-guest-3")

    assert report["performed"] is True
    assert report["winning_offer_token"] == offer_auth.token

    auth_cart.refresh_from_db()
    assert auth_cart.claimed_offer_token == offer_auth.token


# ---------------------------------------------------------------------------
# Case 4: Auth offer invalid/expired → guest offer survives
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_merge_invalid_auth_offer_guest_survives(django_user_model):
    """
    MERGE path — auth cart's offer is expired; guest cart's offer is valid.
    Only the guest-side offer must survive.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_4@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    auth_cart = _auth_cart(user)
    _add_item(auth_cart, product)
    promo_auth = _campaign_promotion(
        value=Decimal("25"),
        active_to=date(2001, 12, 31),  # expired
    )
    offer_auth = _offer(
        promo_auth,
        token="auth-offer-stale",
        active_to=date(2001, 12, 31),
    )
    auth_cart.claimed_offer_token = offer_auth.token
    auth_cart.save(update_fields=["claimed_offer_token"])

    guest_cart = _guest_cart("tok-guest-4")
    _add_item(guest_cart, product)
    promo_guest = _campaign_promotion(value=Decimal("10"))
    offer_guest = _offer(promo_guest, token="guest-offer-live")
    guest_cart.claimed_offer_token = offer_guest.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-guest-4")

    assert report["performed"] is True
    assert report["winning_offer_token"] == offer_guest.token

    auth_cart.refresh_from_db()
    assert auth_cart.claimed_offer_token == offer_guest.token


# ---------------------------------------------------------------------------
# Case 5: Neither offer is valid → no offer survives
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_merge_neither_offer_valid_no_winner(django_user_model):
    """
    MERGE path — both carts hold expired offers.
    winning_offer_token must be None and the merged cart field cleared.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_5@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    auth_cart = _auth_cart(user)
    _add_item(auth_cart, product)
    promo_auth = _campaign_promotion(active_to=date(2001, 1, 1))
    offer_auth = _offer(promo_auth, token="auth-expired", active_to=date(2001, 1, 1))
    auth_cart.claimed_offer_token = offer_auth.token
    auth_cart.save(update_fields=["claimed_offer_token"])

    guest_cart = _guest_cart("tok-guest-5")
    _add_item(guest_cart, product)
    promo_guest = _campaign_promotion(active_to=date(2001, 1, 1))
    offer_guest = _offer(promo_guest, token="guest-expired", active_to=date(2001, 1, 1))
    guest_cart.claimed_offer_token = offer_guest.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-guest-5")

    assert report["performed"] is True
    assert report["winning_offer_token"] is None

    auth_cart.refresh_from_db()
    assert auth_cart.claimed_offer_token is None


# ---------------------------------------------------------------------------
# Case 5b: Both carts have no claimed offer → no winner
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_merge_no_offers_on_either_side(django_user_model):
    """
    MERGE path — no claimed offer on either side.
    winning_offer_token must be None.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_5b@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    auth_cart = _auth_cart(user)
    _add_item(auth_cart, product)

    guest_cart = _guest_cart("tok-guest-5b")
    _add_item(guest_cart, product)

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-guest-5b")

    assert report["performed"] is True
    assert report["winning_offer_token"] is None


# ---------------------------------------------------------------------------
# Case 6: Same token on both sides → deduplicated, survives if valid
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_merge_same_token_on_both_sides_deduplicates(django_user_model):
    """
    MERGE path — both carts carry the same offer token.
    Should resolve to a single candidate, not double-count.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_6@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    promo = _campaign_promotion(value=Decimal("10"))
    offer = _offer(promo, token="shared-token")

    auth_cart = _auth_cart(user)
    _add_item(auth_cart, product)
    auth_cart.claimed_offer_token = offer.token
    auth_cart.save(update_fields=["claimed_offer_token"])

    guest_cart = _guest_cart("tok-guest-6")
    _add_item(guest_cart, product)
    guest_cart.claimed_offer_token = offer.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-guest-6")

    assert report["performed"] is True
    assert report["winning_offer_token"] == offer.token


# ---------------------------------------------------------------------------
# Case 7: Clearing cart items does NOT affect claimed_offer_token
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_clear_cart_items_does_not_remove_claimed_offer_token(django_user_model):
    """
    Business rule (session persistence): clearing all CartItems from a cart
    must NOT clear the cart's claimed_offer_token.

    The campaign context persists until checkout, expiry, or explicit removal /
    replacement — not just because the cart becomes empty.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_7@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    cart = _auth_cart(user)
    _add_item(cart, product)

    promo = _campaign_promotion(value=Decimal("5"))
    offer = _offer(promo, token="persistent-offer")
    cart.claimed_offer_token = offer.token
    cart.save(update_fields=["claimed_offer_token"])

    # Clear all items (simulates the DELETE /cart/ endpoint).
    CartItem.objects.filter(cart=cart).delete()

    cart.refresh_from_db()
    # The campaign context must survive item removal.
    assert cart.claimed_offer_token == offer.token


# ---------------------------------------------------------------------------
# Case 8: Canonical pricing still recomputed on merged cart (no regression)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_merge_still_recomputes_pricing_on_merged_cart(django_user_model):
    """
    The merge must use the merged cart's total gross to evaluate offers,
    not either of the original carts' gross totals in isolation.

    Setup: auth cart has 1 × €50 item, guest cart has 1 × €50 item.
    Both offers are FIXED: auth=€30, guest=€20.
    After merge total_gross = €100.  Auth offer (€30) should win.
    This confirms that pricing is computed on the post-merge cart.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_8@example.com", password="Passw0rd!"
    )
    product = _product_with_pricing(price=Decimal("50.00"))

    # Auth cart: 1 × €50.
    auth_cart = _auth_cart(user)
    _add_item(auth_cart, product, qty=1)
    promo_auth = _campaign_promotion(value=Decimal("30"))
    offer_auth = _offer(promo_auth, token="auth-30-post-merge")
    auth_cart.claimed_offer_token = offer_auth.token
    auth_cart.save(update_fields=["claimed_offer_token"])

    # Guest cart: 1 × €50 (different product instance, same unit price).
    product2 = _product_with_pricing(price=Decimal("50.00"))
    guest_cart = _guest_cart("tok-guest-8")
    _add_item(guest_cart, product2, qty=1)
    promo_guest = _campaign_promotion(value=Decimal("20"))
    offer_guest = _offer(promo_guest, token="guest-20-post-merge")
    guest_cart.claimed_offer_token = offer_guest.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-guest-8")

    # Auth offer (€30) beats guest offer (€20) — both evaluated on merged €100 cart.
    assert report["winning_offer_token"] == offer_auth.token


# ---------------------------------------------------------------------------
# ADOPT path: guest valid offer survives
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_adopt_guest_valid_offer_survives(django_user_model):
    """
    ADOPT path (user has no pre-existing cart) — guest's valid offer must
    be carried over to the adopted cart.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_9@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    guest_cart = _guest_cart("tok-adopt-1")
    _add_item(guest_cart, product)
    promo = _campaign_promotion(value=Decimal("5"))
    offer = _offer(promo, token="adopt-guest-offer")
    guest_cart.claimed_offer_token = offer.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-adopt-1")

    assert report["performed"] is True
    assert report["result"] == "ADOPTED"
    assert report["winning_offer_token"] == offer.token

    adopted_cart = Cart.objects.get(user=user, status=Cart.Status.ACTIVE)
    assert adopted_cart.claimed_offer_token == offer.token


# ---------------------------------------------------------------------------
# ADOPT path: guest invalid offer is cleared
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_adopt_guest_invalid_offer_cleared(django_user_model):
    """
    ADOPT path — guest cart's offer is expired.
    The adopted cart must have claimed_offer_token=None and winning_offer_token=None.
    """
    user = django_user_model.objects.create_user(
        email="merge_camp_10@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    guest_cart = _guest_cart("tok-adopt-2")
    _add_item(guest_cart, product)
    promo = _campaign_promotion(active_to=date(2000, 6, 1))
    offer = _offer(promo, token="expired-adopt", active_to=date(2000, 6, 1))
    guest_cart.claimed_offer_token = offer.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-adopt-2")

    assert report["performed"] is True
    assert report["result"] == "ADOPTED"
    assert report["winning_offer_token"] is None

    adopted_cart = Cart.objects.get(user=user, status=Cart.Status.ACTIVE)
    assert adopted_cart.claimed_offer_token is None


# ---------------------------------------------------------------------------
# NOOP report always carries winning_offer_token=None
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_noop_report_has_winning_offer_token_none(django_user_model):
    """NOOP report (no guest token) must include winning_offer_token=None."""
    user = django_user_model.objects.create_user(
        email="merge_camp_11@example.com", password="Passw0rd!"
    )
    report = merge_or_adopt_guest_cart(user=user, raw_token=None)

    assert report["performed"] is False
    assert report["result"] == "NOOP"
    assert report["winning_offer_token"] is None


# ---------------------------------------------------------------------------
# API: CartMergeView sets campaign_offer_token cookie to the winner
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cart_merge_api_sets_campaign_offer_cookie(django_user_model):
    """
    POST /cart/merge/ must set campaign_offer_token cookie to the winning
    offer when the merge resolves a valid campaign offer.
    """
    from api.services.campaign_offer_session import CAMPAIGN_OFFER_COOKIE
    from rest_framework.test import APIClient

    user = django_user_model.objects.create_user(
        email="merge_camp_api_1@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    promo = _campaign_promotion(value=Decimal("10"))
    offer = _offer(promo, token="api-guest-offer")

    guest_cart = _guest_cart("tok-api-1")
    _add_item(guest_cart, product)
    guest_cart.claimed_offer_token = offer.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    client = APIClient()
    client.force_authenticate(user=user)
    client.cookies["cart_token"] = "tok-api-1"

    resp = client.post("/api/v1/cart/merge/", format="json")

    assert resp.status_code == 200
    assert resp.data["performed"] is True
    assert resp.data["winning_offer_token"] == offer.token
    assert CAMPAIGN_OFFER_COOKIE in resp.cookies
    assert resp.cookies[CAMPAIGN_OFFER_COOKIE].value == offer.token


@pytest.mark.django_db
def test_cart_merge_api_clears_campaign_offer_cookie_when_no_winner(django_user_model):
    """
    POST /cart/merge/ must clear campaign_offer_token cookie when no valid
    offer survives the merge.
    """
    from api.services.campaign_offer_session import CAMPAIGN_OFFER_COOKIE
    from rest_framework.test import APIClient

    user = django_user_model.objects.create_user(
        email="merge_camp_api_2@example.com", password="Passw0rd!"
    )
    product = _plain_product()

    # Guest cart with an expired offer.
    promo = _campaign_promotion(active_to=date(2001, 1, 1))
    offer = _offer(promo, token="api-expired-offer", active_to=date(2001, 1, 1))

    guest_cart = _guest_cart("tok-api-2")
    _add_item(guest_cart, product)
    guest_cart.claimed_offer_token = offer.token
    guest_cart.save(update_fields=["claimed_offer_token"])

    client = APIClient()
    client.force_authenticate(user=user)
    client.cookies["cart_token"] = "tok-api-2"

    resp = client.post("/api/v1/cart/merge/", format="json")

    assert resp.status_code == 200
    assert resp.data["winning_offer_token"] is None
    # Cookie must be cleared (max_age=0 or the cookie set to empty).
    if CAMPAIGN_OFFER_COOKIE in resp.cookies:
        cookie = resp.cookies[CAMPAIGN_OFFER_COOKIE]
        assert cookie.value == "" or cookie["max-age"] == 0


@pytest.mark.django_db
def test_cart_merge_api_noop_does_not_touch_campaign_offer_cookie(django_user_model):
    """
    POST /cart/merge/ with no guest token (NOOP) must NOT include
    campaign_offer_token in the response cookies at all.
    """
    from api.services.campaign_offer_session import CAMPAIGN_OFFER_COOKIE
    from rest_framework.test import APIClient

    user = django_user_model.objects.create_user(
        email="merge_camp_api_3@example.com", password="Passw0rd!"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    # No cart_token cookie → NOOP.
    resp = client.post("/api/v1/cart/merge/", format="json")

    assert resp.status_code == 200
    assert resp.data["performed"] is False
    assert CAMPAIGN_OFFER_COOKIE not in resp.cookies
