"""Tests for the order-level promotion decision engine — Phase 4 / Slice 5C.

Covers the two public contracts:
  - :func:`~discounts.services.order_discount_decision.resolve_order_discount_decision_state`
    (unit-level, direct function calls)
  - The ``campaign_outcome`` and ``order_discount_next_upgrade`` fields
    exposed in the cart API response (integration-level, real HTTP client).

Scenario matrix
---------------
1. PERCENT promotion wins first (only eligible at cart=350).
2. FIXED overtakes later (FIXED becomes eligible at cart=550; equal priority
   so higher benefit wins the tiebreaker).
3. PERCENT overtakes FIXED again (crossover at ~€600.05; equal priority).
4. "Next upgrade" resolves to the crossover point, not just the nearest threshold.
5. Campaign offer is APPLIED when it is the current winner.
6. Campaign offer is SUPERSEDED when another promotion superseded the offer.
7. FE-facing cart payload is deterministic across identical inputs.

Priority-first policy tests (added in corrective alignment)
------------------------------------------------------------
8.  Higher priority beats higher benefit (priority is king).
9.  Equal priority — higher benefit wins.
10. Equal priority, equal benefit — lower id is stable tiebreaker.
11. Different-priority PERCENT/FIXED crossover is NOT surfaced as upgrade.
12. Campaign outcome respects priority-first: high-priority low-benefit auto
    supersedes low-priority high-benefit campaign offer.
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
from discounts.services.order_discount_decision import (
    resolve_order_discount_decision_state,
)
from products.models import Product, TaxClass

CLAIM_URL = "/api/v1/cart/offer/claim/"
CART_URL = "/api/v1/cart/"
CART_ITEMS_URL = "/api/v1/cart/items/"

# Counter to produce unique promo codes across the test module.
_SEQ = 0


def _next_code() -> str:
    global _SEQ
    _SEQ += 1
    return f"DEC-{_SEQ:05d}"


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------


def _tax_class(tag: str = "zero") -> TaxClass:
    return TaxClass.objects.get_or_create(
        code=f"dec-zero-{tag}",
        defaults={"name": f"Zero Rate ({tag})", "rate": Decimal("0")},
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
    minimum_order_value: Decimal | None = None,
    name: str | None = None,
) -> OrderPromotion:
    return OrderPromotion.objects.create(
        name=name or f"Auto {promo_type} {value}",
        code=_next_code(),
        type=promo_type,
        value=value,
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=priority,
        is_active=True,
        minimum_order_value=minimum_order_value,
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


# ===========================================================================
# Unit tests — decision service directly
# ===========================================================================


@pytest.mark.django_db
def test_percent_wins_when_only_eligible():
    """At cart=350, PERCENT-10% (€35) is the only eligible promo.

    FIXED-€60 requires €500 so its threshold is the next upgrade.
    """
    percent_promo = _auto_apply(
        Decimal("10"),
        promo_type=PromotionType.PERCENT,
        name="Percent 10%",
        minimum_order_value=None,
    )
    _auto_apply(
        Decimal("60"),
        promo_type=PromotionType.FIXED,
        name="Fixed 60",
        minimum_order_value=Decimal("500"),
    )

    state = resolve_order_discount_decision_state(
        cart_gross=Decimal("350"),
        currency="EUR",
        current_winner=percent_promo,
    )

    assert state.campaign_outcome is None
    # At €500 FIXED becomes eligible with benefit €60 > PERCENT €50 — upgrade.
    assert state.next_upgrade is not None
    assert state.next_upgrade.threshold == Decimal("500.00")
    assert state.next_upgrade.remaining == Decimal("150.00")
    assert state.next_upgrade.promotion_name == "Fixed 60"


@pytest.mark.django_db
def test_fixed_overtakes_percent_at_threshold():
    """At cart=550, FIXED-€60 beats PERCENT-€55.  The next winner change
    is the PERCENT/FIXED crossover (~€600.05) where PERCENT overtakes again.
    """
    percent_promo = _auto_apply(
        Decimal("10"),
        promo_type=PromotionType.PERCENT,
        name="Percent 10%",
        minimum_order_value=None,
    )
    fixed_promo = _auto_apply(
        Decimal("60"),
        promo_type=PromotionType.FIXED,
        name="Fixed 60",
        minimum_order_value=Decimal("500"),
    )

    state = resolve_order_discount_decision_state(
        cart_gross=Decimal("550"),
        currency="EUR",
        current_winner=fixed_promo,
    )

    assert state.campaign_outcome is None
    assert state.next_upgrade is not None
    assert state.next_upgrade.promotion_name == percent_promo.name
    # Threshold must be > current cart value.
    assert state.next_upgrade.threshold > Decimal("550")
    assert state.next_upgrade.remaining > Decimal("0")


@pytest.mark.django_db
def test_percent_overtakes_fixed_at_crossover():
    """Verify the analytical crossover formula.

    For PERCENT-10% vs FIXED-€60:
        crossover = ceil((60 + 0.005) × 100 / 10, 2 dp) = ceil(600.05) = 600.05
    At cart=600.05: PERCENT benefit = (600.05 × 10/100) = 60.005 → rounds to €60.01
    exceeds FIXED benefit €60.00 → PERCENT wins.
    """
    percent_promo = _auto_apply(
        Decimal("10"),
        promo_type=PromotionType.PERCENT,
        name="Percent 10%",
        minimum_order_value=None,
    )
    fixed_promo = _auto_apply(
        Decimal("60"),
        promo_type=PromotionType.FIXED,
        name="Fixed 60",
        minimum_order_value=Decimal("500"),
    )

    # At crossover (600.05) PERCENT becomes the winner again.
    state_at_crossover = resolve_order_discount_decision_state(
        cart_gross=Decimal("600.05"),
        currency="EUR",
        current_winner=percent_promo,
    )
    # PERCENT is now the winner at cart=600.05; no higher promotion exists.
    assert state_at_crossover.next_upgrade is None

    # Just below the crossover the winner is still FIXED (599.90).
    state_below = resolve_order_discount_decision_state(
        cart_gross=Decimal("599.90"),
        currency="EUR",
        current_winner=fixed_promo,
    )
    # The next upgrade should be at the crossover.
    assert state_below.next_upgrade is not None
    assert state_below.next_upgrade.promotion_name == percent_promo.name
    crossover_threshold = state_below.next_upgrade.threshold
    assert crossover_threshold == Decimal("600.05"), (
        f"Expected crossover at 600.05, got {crossover_threshold}"
    )


@pytest.mark.django_db
def test_next_upgrade_is_winner_change_not_nearest_threshold():
    """At cart=550 (winner=FIXED), the FIXED threshold is already passed.

    The nearest *unapplied* threshold would be €500 (already passed).
    The next meaningful upgrade is the PERCENT crossover at ~€600.05 —
    NOT some earlier threshold.  This specifically guards against
    returning the nearest threshold numerically regardless of whether the
    winner would actually change.
    """
    _auto_apply(
        Decimal("10"),
        promo_type=PromotionType.PERCENT,
        name="Percent 10%",
        minimum_order_value=None,
    )
    fixed_promo = _auto_apply(
        Decimal("60"),
        promo_type=PromotionType.FIXED,
        name="Fixed 60",
        minimum_order_value=Decimal("500"),
    )

    state = resolve_order_discount_decision_state(
        cart_gross=Decimal("550"),
        currency="EUR",
        current_winner=fixed_promo,
    )

    assert state.next_upgrade is not None
    # The upgrade threshold must be strictly above cart_gross.
    assert state.next_upgrade.threshold > Decimal("550")
    # Specifically the crossover, not the already-passed €500 threshold.
    assert state.next_upgrade.threshold != Decimal("500.00")


@pytest.mark.django_db
def test_campaign_offer_applied_when_it_wins():
    """When the campaign offer IS the current exclusive winner, outcome = APPLIED."""
    camp_promo = _campaign(Decimal("50"), name="BigSaver")

    state = resolve_order_discount_decision_state(
        cart_gross=Decimal("200"),
        currency="EUR",
        current_winner=camp_promo,
        campaign_offer_promotion=camp_promo,
    )

    assert state.campaign_outcome == "APPLIED"


@pytest.mark.django_db
def test_campaign_offer_superseded_when_auto_apply_wins():
    """When a better AUTO_APPLY wins instead of the campaign offer,
    outcome = SUPERSEDED.
    """
    auto_promo = _auto_apply(Decimal("60"), name="BigAutoAply")
    camp_promo = _campaign(Decimal("5"), promo_type=PromotionType.PERCENT, name="SmallCamp")

    # Auto-apply wins (€60 > 5% of cart).
    state = resolve_order_discount_decision_state(
        cart_gross=Decimal("300"),
        currency="EUR",
        current_winner=auto_promo,
        campaign_offer_promotion=camp_promo,
    )

    assert state.campaign_outcome == "SUPERSEDED"


@pytest.mark.django_db
def test_decision_state_deterministic():
    """Identical inputs always produce identical outputs (no side effects)."""
    percent_promo = _auto_apply(
        Decimal("10"),
        promo_type=PromotionType.PERCENT,
        name="Percent 10% det",
        minimum_order_value=None,
    )
    _auto_apply(
        Decimal("60"),
        promo_type=PromotionType.FIXED,
        name="Fixed 60 det",
        minimum_order_value=Decimal("500"),
    )

    state1 = resolve_order_discount_decision_state(
        cart_gross=Decimal("350"),
        currency="EUR",
        current_winner=percent_promo,
    )
    state2 = resolve_order_discount_decision_state(
        cart_gross=Decimal("350"),
        currency="EUR",
        current_winner=percent_promo,
    )

    assert state1.next_upgrade is not None
    assert state2.next_upgrade is not None
    assert state1.next_upgrade.threshold == state2.next_upgrade.threshold
    assert state1.next_upgrade.remaining == state2.next_upgrade.remaining
    assert state1.next_upgrade.promotion_name == state2.next_upgrade.promotion_name


# ===========================================================================
# Priority-first winner policy — corrective alignment tests
# ===========================================================================


@pytest.mark.django_db
def test_higher_priority_beats_higher_benefit():
    """A lower-value promo with higher priority wins over a higher-value promo.

    Priority is the first criterion.  Benefit is only a tiebreaker when
    priorities are equal.  This test specifically guards against accidental
    reversion to a benefit-first policy.
    """
    # priority=10 but tiny discount
    high_prio = _auto_apply(
        Decimal("5"),
        promo_type=PromotionType.FIXED,
        priority=10,
        name="HighPrioLowBenefit",
    )
    # priority=1 but large discount
    _auto_apply(
        Decimal("200"),
        promo_type=PromotionType.FIXED,
        priority=1,
        name="LowPrioHighBenefit",
    )

    # high_prio (priority=10) is the current winner — correct under priority-first.
    # No transition point can ever flip the winner to LowPrioHighBenefit because
    # HighPrioLowBenefit always has a higher priority.
    state = resolve_order_discount_decision_state(
        cart_gross=Decimal("500"),
        currency="EUR",
        current_winner=high_prio,
    )
    # No upgrade should be signalled — LowPrioHighBenefit can never displace
    # HighPrioLowBenefit under priority-first selection.
    assert state.next_upgrade is None


@pytest.mark.django_db
def test_equal_priority_higher_benefit_wins():
    """When priorities are equal, the promotion giving the higher gross discount wins."""
    # Same priority — benefit tiebreaker activates.
    fixed = _auto_apply(
        Decimal("50"),
        promo_type=PromotionType.FIXED,
        priority=5,
        name="Fixed50EqPrio",
    )
    percent = _auto_apply(
        Decimal("10"),
        promo_type=PromotionType.PERCENT,
        priority=5,
        name="Percent10EqPrio",
        minimum_order_value=None,
    )

    # At cart=600: PERCENT gives 60 > FIXED 50 → PERCENT wins on benefit.
    # At this point percent IS the winner; no further upgrade expected.
    state = resolve_order_discount_decision_state(
        cart_gross=Decimal("600"),
        currency="EUR",
        current_winner=percent,
    )
    assert state.next_upgrade is None

    # At cart=400: FIXED gives 50, PERCENT gives 40 → FIXED wins.
    state_fixed_wins = resolve_order_discount_decision_state(
        cart_gross=Decimal("400"),
        currency="EUR",
        current_winner=fixed,
    )
    # Crossover at ceil((50+0.005)×100/10) = ceil(500.05) = 500.05
    assert state_fixed_wins.next_upgrade is not None
    assert state_fixed_wins.next_upgrade.promotion_name == percent.name
    assert state_fixed_wins.next_upgrade.threshold == Decimal("500.05")


@pytest.mark.django_db
def test_equal_priority_equal_benefit_lower_id_wins():
    """Stable tiebreaker: lower id wins when priority and benefit are equal."""
    p1 = _auto_apply(
        Decimal("50"),
        promo_type=PromotionType.FIXED,
        priority=5,
        name="EqualP1",
    )
    p2 = _auto_apply(
        Decimal("50"),
        promo_type=PromotionType.FIXED,
        priority=5,
        name="EqualP2",
    )
    # Helper creates in order, so p1.id < p2.id.
    assert p1.id < p2.id

    # p1 (lower id) is the stable winner; p2 has identical priority and benefit.
    state = resolve_order_discount_decision_state(
        cart_gross=Decimal("200"),
        currency="EUR",
        current_winner=p1,
    )
    # p2 can never displace p1 (same priority, same benefit, higher id).
    assert state.next_upgrade is None


@pytest.mark.django_db
def test_different_priority_crossover_never_triggers_upgrade():
    """PERCENT/FIXED crossovers between different-priority promos are not upgrades.

    Reproduces the real-world scenario that caused false "Spend EUR 3689 more"
    banners:

    - OL-Fixed-500 (priority=1, FIXED=500, min=500): always wins when eligible.
    - OL-Percent-40 (priority=0, PERCENT=40%, min=300): can never win while
      OL-Fixed-500 is active (lower priority).

    Above the crossover value where 40% × cart > 500 (i.e. cart > 1250),
    OL-Percent-40 would give more gross benefit.  However, under priority-first
    selection OL-Fixed-500 still wins because priority=1 > priority=0.
    No upgrade banner should ever appear in this configuration.
    """
    fixed_high_prio = _auto_apply(
        Decimal("500"),
        promo_type=PromotionType.FIXED,
        priority=1,
        minimum_order_value=Decimal("500"),
        name="FixedHighPrio",
    )
    _auto_apply(
        Decimal("40"),
        promo_type=PromotionType.PERCENT,
        priority=0,
        minimum_order_value=Decimal("300"),
        name="PercentLowPrio",
    )

    # Well above both thresholds and above the benefit crossover (~1250).
    for cart_value in (Decimal("1200.00"), Decimal("1310.30"), Decimal("5000.00")):
        state = resolve_order_discount_decision_state(
            cart_gross=cart_value,
            currency="EUR",
            current_winner=fixed_high_prio,
        )
        assert state.next_upgrade is None, (
            f"Expected no upgrade at cart={cart_value}, "
            f"got threshold={state.next_upgrade.threshold if state.next_upgrade else None}"
        )


@pytest.mark.django_db
def test_campaign_outcome_superseded_by_higher_priority_lower_benefit():
    """Campaign offer is SUPERSEDED when a higher-priority auto-apply wins,
    even if the campaign offer gives a larger gross discount.

    Priority-first means the auto-apply promotion wins regardless of benefit.
    """
    # Auto-apply: high priority, tiny discount.
    auto_high_prio = _auto_apply(
        Decimal("5"),
        promo_type=PromotionType.FIXED,
        priority=10,
        name="HighPrioAutoApply",
    )
    # Campaign offer: lower priority, generous discount.
    camp_low_prio = _campaign(
        Decimal("50"),
        promo_type=PromotionType.FIXED,
        priority=1,
        name="HighBenefitCampaign",
    )

    # Pricing engine (priority-first) picks auto_high_prio as current_winner.
    state = resolve_order_discount_decision_state(
        cart_gross=Decimal("200"),
        currency="EUR",
        current_winner=auto_high_prio,
        campaign_offer_promotion=camp_low_prio,
    )
    assert state.campaign_outcome == "SUPERSEDED"


# ===========================================================================
# Integration tests — cart API payload
# ===========================================================================


@pytest.mark.django_db
def test_api_next_upgrade_present_in_cart_payload():
    """Cart API exposes order_discount_next_upgrade when a better future promo exists."""
    _auto_apply(
        Decimal("10"),
        promo_type=PromotionType.PERCENT,
        name="Percent 10 API",
        minimum_order_value=None,
        priority=5,
    )
    _auto_apply(
        Decimal("60"),
        promo_type=PromotionType.FIXED,
        name="Fixed 60 API",
        minimum_order_value=Decimal("500"),
        priority=5,
    )

    # Cart with €350 subtotal: PERCENT wins (€35), FIXED requires €500.
    product = _product(Decimal("350.00"))
    client = APIClient()
    _add_item(client, product)

    totals = _totals(client)

    assert totals["order_discount_applied"] is True
    upgrade = totals["order_discount_next_upgrade"]
    assert upgrade is not None
    assert Decimal(upgrade["threshold"]) == Decimal("500.00")
    assert Decimal(upgrade["remaining"]) == Decimal("150.00")
    assert upgrade["promotion_name"] == "Fixed 60 API"


@pytest.mark.django_db
def test_api_no_next_upgrade_when_winner_is_best_possible():
    """When no higher promotion exists, order_discount_next_upgrade is null."""
    _auto_apply(Decimal("50"), promo_type=PromotionType.FIXED, name="Only Promo")

    product = _product(Decimal("100.00"))
    client = APIClient()
    _add_item(client, product)

    totals = _totals(client)

    assert totals["order_discount_applied"] is True
    assert totals["order_discount_next_upgrade"] is None


@pytest.mark.django_db
def test_api_campaign_outcome_applied_in_payload():
    """When campaign offer wins, cart payload reports campaign_outcome='APPLIED'."""
    camp_promo = _campaign(Decimal("40"), name="BigCampaign")
    offer = _offer(camp_promo)
    _auto_apply(Decimal("10"), name="SmallAuto")  # smaller, will lose

    product = _product(Decimal("100.00"))
    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    assert totals["campaign_outcome"] == "APPLIED"
    assert totals["order_discount_promotion_name"] == camp_promo.name


@pytest.mark.django_db
def test_api_campaign_outcome_superseded_in_payload():
    """When auto-apply wins, cart payload reports campaign_outcome='SUPERSEDED'."""
    camp_promo = _campaign(Decimal("5"), promo_type=PromotionType.PERCENT, name="TinyCamp")
    offer = _offer(camp_promo)
    _auto_apply(Decimal("50"), name="BigAuto")  # wins against 5%

    product = _product(Decimal("100.00"))
    client = APIClient()
    _add_item(client, product)
    _claim(client, offer)

    totals = _totals(client)

    assert totals["campaign_outcome"] == "SUPERSEDED"
    # The winning discount is the auto-apply, not the campaign.
    assert totals["order_discount_promotion_name"] == "BigAuto"


@pytest.mark.django_db
def test_api_campaign_outcome_null_without_claimed_offer():
    """Without a campaign offer cookie, campaign_outcome is null."""
    _auto_apply(Decimal("20"), name="AutoPromo")

    product = _product(Decimal("100.00"))
    client = APIClient()
    _add_item(client, product)

    totals = _totals(client)

    assert totals["campaign_outcome"] is None
