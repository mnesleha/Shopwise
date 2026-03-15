"""API tests — exclusive order-level promotion winner selection.

Ensures that when multiple EXCLUSIVE order-level promotions are eligible
(mix of AUTO_APPLY and CAMPAIGN_APPLY), only the single winner is reflected
in the cart/checkout pricing payload.

Winner selection rule (ADR-042 §4.2):
1. Highest gross benefit on the current cart.
2. Highest explicit priority.
3. Lowest id as stable tie-breaker.

Test matrix
-----------
- Campaign offer gives higher benefit than AUTO_APPLY → campaign offer wins.
- AUTO_APPLY gives higher benefit than campaign offer → AUTO_APPLY wins.
- Equal benefit → promotion with higher priority wins.
- Equal benefit and equal priority → promotion with lower id wins.
- Exactly one order-level discount is applied (exclusivity invariant).
- Non-winning promotion does not appear as the applied discount.
"""

from decimal import Decimal

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

CLAIM_URL = "/api/v1/cart/offer/claim/"
CART_URL = "/api/v1/cart/"
CART_ITEMS_URL = "/api/v1/cart/items/"

_SEQ = 0


def _next_code() -> str:
    global _SEQ
    _SEQ += 1
    return f"EXCL-{_SEQ:05d}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tax_class(name: str = "zero") -> TaxClass:
    return TaxClass.objects.get_or_create(
        code=f"excl-zero-{name}",
        defaults={"name": f"Zero Rate ({name})", "rate": Decimal("0")},
    )[0]


def _product(price_net: Decimal = Decimal("100.00")) -> Product:
    tc = _tax_class(str(price_net).replace(".", "_"))
    return Product.objects.create(
        name=f"Widget {price_net}",
        price=price_net,
        stock_quantity=100,
        is_active=True,
        price_net_amount=price_net,
        currency="EUR",
        tax_class=tc,
    )


def _auto_apply(
    value: Decimal,
    promo_type: str = PromotionType.FIXED,
    priority: int = 5,
) -> OrderPromotion:
    return OrderPromotion.objects.create(
        name=f"Auto {promo_type} {value}",
        code=_next_code(),
        type=promo_type,
        value=value,
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=priority,
        is_active=True,
        minimum_order_value=None,
        active_from=None,
        active_to=None,
    )


def _campaign(
    value: Decimal,
    promo_type: str = PromotionType.FIXED,
    priority: int = 5,
    name: str | None = None,
) -> OrderPromotion:
    return OrderPromotion.objects.create(
        name=name or f"Campaign {promo_type} {value}",
        code=_next_code(),
        type=promo_type,
        value=value,
        acquisition_mode=AcquisitionMode.CAMPAIGN_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=priority,
        is_active=True,
        minimum_order_value=None,
        active_from=None,
        active_to=None,
    )


def _offer(promo: OrderPromotion) -> Offer:
    import uuid
    return Offer.objects.create(
        token=str(uuid.uuid4()),
        promotion=promo,
        status=OfferStatus.CREATED,
        is_active=True,
    )


def _add_item(client: APIClient, product: Product, qty: int = 1) -> None:
    r = client.post(
        CART_ITEMS_URL,
        {"product_id": product.id, "quantity": qty},
        format="json",
    )
    assert r.status_code in (200, 201), r.json()


def _claim(client: APIClient, offer: Offer) -> None:
    r = client.post(CLAIM_URL, {"token": offer.token}, format="json")
    assert r.status_code == 200, r.json()


def _totals(client: APIClient) -> dict:
    r = client.get(CART_URL)
    assert r.status_code == 200, r.json()
    return r.json()["totals"]


# ---------------------------------------------------------------------------
# Winner selection: benefit comparison
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_campaign_offer_wins_when_it_gives_higher_benefit():
    """Campaign FIXED-30 beats AUTO_APPLY FIXED-10 on a €100 cart."""
    auto = _auto_apply(value=Decimal("10"))
    camp_promo = _campaign(value=Decimal("30"))
    offer = _offer(camp_promo)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    assert totals["order_discount_applied"] is True
    assert Decimal(totals["order_discount_amount"]) == Decimal("30.00")
    # The winning promotion name must be the campaign one.
    assert totals["order_discount_promotion_name"] == camp_promo.name
    assert totals["order_discount_promotion_name"] != auto.name


@pytest.mark.django_db
def test_auto_apply_wins_when_it_gives_higher_benefit():
    """AUTO_APPLY FIXED-50 beats campaign FIXED-10 on a €100 cart."""
    auto = _auto_apply(value=Decimal("50"))
    camp_promo = _campaign(value=Decimal("10"))
    offer = _offer(camp_promo)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    assert totals["order_discount_applied"] is True
    assert Decimal(totals["order_discount_amount"]) == Decimal("50.00")
    # The winning promotion must be the AUTO_APPLY one.
    assert totals["order_discount_promotion_name"] == auto.name
    assert totals["order_discount_promotion_name"] != camp_promo.name


@pytest.mark.django_db
def test_percent_vs_fixed_winner_is_highest_benefit():
    """20% of €100 = €20 beats FIXED €15; so PERCENT campaign wins."""
    _auto_apply(value=Decimal("15"), promo_type=PromotionType.FIXED)
    camp_promo = _campaign(
        value=Decimal("20"),
        promo_type=PromotionType.PERCENT,
        name="Percent Campaign",
    )
    offer = _offer(camp_promo)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    # 20% of 100 = 20 > 15 → campaign PERCENT wins.
    assert Decimal(totals["order_discount_amount"]) == Decimal("20.00")
    assert totals["order_discount_promotion_name"] == camp_promo.name


# ---------------------------------------------------------------------------
# Winner selection: tie-breakers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_equal_benefit_higher_priority_wins():
    """When campaign and AUTO_APPLY both give €20, higher priority wins."""
    # AUTO_APPLY has priority=10, campaign has priority=5.
    auto = _auto_apply(value=Decimal("20"), priority=10)
    camp_promo = _campaign(value=Decimal("20"), priority=5)
    offer = _offer(camp_promo)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    # AUTO_APPLY has higher priority → it wins despite equal benefit.
    assert totals["order_discount_promotion_name"] == auto.name


@pytest.mark.django_db
def test_equal_benefit_equal_priority_lower_id_wins():
    """When benefit and priority are equal, the promotion with the lower id wins."""
    # Create the campaign promotion first so it has a lower id.
    camp_promo = _campaign(value=Decimal("20"), priority=5, name="Campaign First")
    auto = _auto_apply(value=Decimal("20"), priority=5)
    assert camp_promo.id < auto.id, "campaign must have lower id for this test"

    offer = _offer(camp_promo)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    # Lower id (campaign) wins on full tie.
    assert totals["order_discount_promotion_name"] == camp_promo.name
    assert totals["order_discount_promotion_name"] != auto.name


@pytest.mark.django_db
def test_equal_benefit_equal_priority_auto_lower_id_wins():
    """When AUTO_APPLY has the lower id, it wins on a full tie."""
    auto = _auto_apply(value=Decimal("20"), priority=5)
    camp_promo = _campaign(value=Decimal("20"), priority=5, name="Campaign Second")
    assert auto.id < camp_promo.id, "auto must have lower id for this test"

    offer = _offer(camp_promo)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    # AUTO_APPLY has lower id → wins.
    assert totals["order_discount_promotion_name"] == auto.name


# ---------------------------------------------------------------------------
# Exclusivity invariant
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_only_one_order_discount_is_applied():
    """Only a single winning order-level discount is reflected — no multi-winner state."""
    _auto_apply(value=Decimal("10"), priority=5)
    camp_promo = _campaign(value=Decimal("20"), priority=10)
    offer = _offer(camp_promo)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    # Exactly one order discount is in the payload.
    assert totals["order_discount_applied"] is True
    # The amount is the winner's amount, not the sum of both.
    assert Decimal(totals["order_discount_amount"]) == Decimal("20.00")


@pytest.mark.django_db
def test_non_winning_campaign_does_not_appear_as_applied():
    """Non-winning campaign promotion name must not be the applied_promotion_name."""
    auto = _auto_apply(value=Decimal("50"), priority=10)
    camp_promo = _campaign(value=Decimal("5"), priority=1, name="Tiny Campaign")
    offer = _offer(camp_promo)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    assert totals["order_discount_promotion_name"] == auto.name
    # Non-winner must not leak into the promotion name field.
    assert "Tiny Campaign" not in (totals.get("order_discount_promotion_name") or "")


@pytest.mark.django_db
def test_cart_without_claimed_offer_uses_auto_apply_normally():
    """When no campaign offer is claimed the AUTO_APPLY promotion resolves as normal."""
    auto = _auto_apply(value=Decimal("15"), priority=5)
    product = _product(price_net=Decimal("100.00"))

    client = APIClient()
    _add_item(client, product)

    totals = _totals(client)

    assert totals["order_discount_applied"] is True
    assert totals["order_discount_promotion_name"] == auto.name
    assert Decimal(totals["order_discount_amount"]) == Decimal("15.00")
