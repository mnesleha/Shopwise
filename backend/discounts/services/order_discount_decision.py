"""Order-level promotion decision engine — Phase 4 / Slice 5C.

Responsibility:
    Given the current cart gross total, the current winning promotion, and
    optionally a claimed campaign offer promotion, determine:

    1. **Campaign offer outcome** — whether the claimed offer is the current
       winner (``"APPLIED"``) or was superseded by another promotion
       (``"SUPERSEDED"``).

    2. **Next meaningful winner transition** — the next cart-value point at
       which the winning order-level promotion changes to one that gives
       **strictly more** customer benefit at that cart value.  It is NOT
       simply the next threshold numerically — the actual winner (under the
       priority-first EXCLUSIVE rule) must change AND the customer must
       receive a higher gross discount.

EXCLUSIVE winner-selection policy
-----------------------------------
All resolution in this module uses the same benefit-first rule applied by
``resolve_auto_apply_order_promotion`` and
``_pick_exclusive_promotion_winner`` in the pricing engine:

    1. **Highest customer benefit** (gross discount at the evaluation cart
       value) — the customer always receives the best available discount.
    2. **Highest priority** — merchant-configured; secondary tiebreaker when
       two promotions give equal gross benefit.
    3. **Lowest id** — stable, deterministic final fallback.

This means any pair of promotions can swap winner positions as the cart
value grows (PERCENT overtakes FIXED at the crossover point), regardless
of their configured priorities.  Crossover analysis is therefore performed
for *all* PERCENT/FIXED pairs, not only same-priority ones.

Types of transition points considered
--------------------------------------
- **Threshold crossings**: the ``minimum_order_value`` of a currently-
  ineligible promotion being reached.
- **PERCENT/FIXED crossovers**: the first cart value at which a PERCENT
  promotion's quantised gross benefit strictly exceeds a FIXED promotion's
  benefit.  Computed **only for pairs with equal priority**, since promos
  with different priorities never swap winner positions regardless of
  benefit::

      threshold = ceil((FIXED.value + 0.005) × 100 / PERCENT.value, 2 dp)

  At this cart value ``(cart × PERCENT.value / 100)`` rounded to 2 dp
  equals ``FIXED.value + 0.01``, so PERCENT strictly wins under the
  benefit tiebreaker.

Public API
----------
- :func:`resolve_order_discount_decision_state` — main entry point.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from discounts.models import AcquisitionMode, OrderPromotion, PromotionType


_QUANTIZE = Decimal("0.01")


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class OrderDiscountUpgrade:
    """Describes the next cart value at which the winning promotion improves.

    Attributes
    ----------
    threshold:
        The cart gross total (2-decimal ``Decimal``) at which the better
        promotion becomes the winner.  The customer needs to reach this
        value.
    remaining:
        ``threshold − current_cart_gross`` — additional spend required.
    promotion_name:
        Human-readable name of the next winning promotion; safe to display
        to the customer without revealing internal mechanics.
    currency:
        ISO 4217 currency code for all monetary amounts.
    """

    threshold: Decimal
    remaining: Decimal
    promotion_name: str
    currency: str


@dataclass
class OrderDiscountDecisionState:
    """Result of :func:`resolve_order_discount_decision_state`.

    Attributes
    ----------
    campaign_outcome:
        ``"APPLIED"`` — the claimed campaign offer is the current winning
        promotion.
        ``"SUPERSEDED"`` — a better auto-apply promotion is already active
        so the campaign offer did not win.
        ``None`` — no campaign offer is involved in this pricing context.
    next_upgrade:
        The next upgrade opportunity, or ``None`` when no better promotion
        exists at any higher cart value.
    """

    campaign_outcome: Optional[str]
    next_upgrade: Optional[OrderDiscountUpgrade]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_all_active_auto_apply_promotions() -> list:
    """Return all active AUTO_APPLY ``OrderPromotion`` objects.

    Unlike :func:`~discounts.services.auto_apply_resolver.resolve_all_eligible_auto_apply_promotions`,
    this function deliberately ignores ``minimum_order_value`` so the
    decision engine can analyse future transitions to promotions that are
    not yet eligible at the current cart value.
    """
    now = timezone.now()
    return list(
        OrderPromotion.objects.filter(
            acquisition_mode=AcquisitionMode.AUTO_APPLY,
            is_active=True,
        )
        .filter(
            Q(active_from__isnull=True) | Q(active_from__lte=now),
            Q(active_to__isnull=True) | Q(active_to__gte=now),
        )
        .order_by("-priority", "id")
    )


def _compute_gross_discount(promotion: "OrderPromotion", total_gross: Decimal) -> Decimal:
    """Return the gross discount a promotion would yield on *total_gross*.

    Duplicated locally from ``carts.services.pricing`` to avoid a circular
    import between ``discounts`` and ``carts``.

    Parameters
    ----------
    promotion:
        An ``OrderPromotion`` instance.
    total_gross:
        Cart gross total to evaluate against.

    Returns
    -------
    Decimal
        Gross discount amount (≥ 0, ≤ total_gross), 2-decimal precision.
    """
    if total_gross <= Decimal(0):
        return Decimal("0.00")
    if promotion.type == PromotionType.PERCENT:
        return (total_gross * promotion.value / Decimal("100")).quantize(
            _QUANTIZE, ROUND_HALF_UP
        )
    # FIXED — capped at the available gross.
    return min(promotion.value, total_gross).quantize(_QUANTIZE, ROUND_HALF_UP)


def _pick_winner(candidates: list, total_gross: Decimal) -> Optional["OrderPromotion"]:
    """Select the EXCLUSIVE winner from *candidates* at *total_gross*.

    Uses the benefit-first EXCLUSIVE rule, identical to
    ``carts.services.pricing._pick_exclusive_promotion_winner``:

    1. Highest gross benefit evaluated on *total_gross*.
    2. Highest ``priority`` — secondary tiebreaker.
    3. Lowest ``id`` as a stable deterministic fallback.

    Parameters
    ----------
    candidates:
        List of ``OrderPromotion`` instances to consider.
    total_gross:
        Cart gross total at which to evaluate each candidate's benefit.

    Returns
    -------
    OrderPromotion or None
        The single winning promotion, or ``None`` when *candidates* is empty.
    """
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda p: (
            _compute_gross_discount(p, total_gross),
            p.priority,
            -p.id,
        ),
    )


def _collect_transition_points(
    all_candidates: list,
    cart_gross: Decimal,
) -> list:
    """Return sorted candidate cart-gross values > *cart_gross* where the winner might change.

    Collects two types of transition points:

    1. **Threshold crossings** — the ``minimum_order_value`` of each
       candidate promotion whose threshold exceeds the current *cart_gross*.

    2. **PERCENT/FIXED crossovers** — for each (PERCENT, FIXED) pair in
       *all_candidates*, the first cart value (2 dp) at which the PERCENT
       promotion's quantised benefit strictly exceeds the FIXED benefit::

           crossover = ceil((FIXED.value + 0.005) × 100 / PERCENT.value, 2 dp)

       Adding ``0.005`` before dividing shifts the ``ROUND_HALF_UP``
       boundary by one cent so the quantised PERCENT benefit equals
       ``FIXED.value + 0.01`` at the returned crossover value.

    Parameters
    ----------
    all_candidates:
        All candidate promotions to scan (eligibility not pre-filtered).
    cart_gross:
        Current cart gross; only transition points *above* this are returned.

    Returns
    -------
    list[Decimal]
        Sorted (ascending) list of distinct transition points.
    """
    points: set = set()

    # Type 1: threshold crossings.
    for p in all_candidates:
        if p.minimum_order_value is not None and p.minimum_order_value > cart_gross:
            points.add(p.minimum_order_value.quantize(_QUANTIZE, ROUND_HALF_UP))

    # Type 2: PERCENT/FIXED crossovers.
    # Under benefit-first policy every PERCENT/FIXED pair can swap winner
    # positions at the crossover cart value, regardless of their priorities.
    # We compute the crossover for every pair so no real transition is missed.
    percent_promos = [p for p in all_candidates if p.type == PromotionType.PERCENT]
    fixed_promos = [p for p in all_candidates if p.type == PromotionType.FIXED]

    for pp in percent_promos:
        if pp.value <= 0:
            continue
        for fp in fixed_promos:
            # Under benefit-first policy every PERCENT/FIXED pair can swap
            # winner positions at the crossover value regardless of priority.
            # First cart value where (cart × pp.value / 100) quantised with
            # ROUND_HALF_UP is strictly > fp.value.  The +0.005 numerator
            # offset shifts the rounding boundary by exactly one cent.
            crossover = (
                (fp.value + Decimal("0.005")) * Decimal("100") / pp.value
            ).quantize(_QUANTIZE, ROUND_CEILING)
            if crossover > cart_gross:
                points.add(crossover)

    return sorted(points)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_order_discount_decision_state(
    cart_gross: Decimal,
    currency: str,
    current_winner: Optional["OrderPromotion"],
    campaign_offer_promotion: Optional["OrderPromotion"] = None,
) -> "OrderDiscountDecisionState":
    """Determine campaign outcome and next meaningful winner transition.

    Parameters
    ----------
    cart_gross:
        Post-line-promotion cart total
        (``CartTotalsResult.total_gross.amount``).
    currency:
        ISO 4217 currency code.
    current_winner:
        The promotion selected as the exclusive winner by the pricing engine
        for the *current* cart value.  ``None`` when no promotion applies.
    campaign_offer_promotion:
        The ``OrderPromotion`` from a claimed campaign offer, if the
        serializer detected one in the request cookie.  When provided, the
        campaign outcome is returned.  ``None`` means no campaign offer is
        involved and ``campaign_outcome`` will be ``None``.

    Returns
    -------
    OrderDiscountDecisionState
        Immutable result with ``campaign_outcome`` and ``next_upgrade``.
    """
    # ── Campaign outcome ──────────────────────────────────────────────────────
    campaign_outcome: Optional[str] = None
    if campaign_offer_promotion is not None:
        if (
            current_winner is not None
            and current_winner.id == campaign_offer_promotion.id
        ):
            campaign_outcome = "APPLIED"
        else:
            campaign_outcome = "SUPERSEDED"

    # ── Build candidate pool for transition analysis ──────────────────────────
    # Fetch all active AUTO_APPLY promotions regardless of minimum_order_value
    # so that future threshold/crossover transitions are visible.
    all_auto_apply = _get_all_active_auto_apply_promotions()

    if campaign_offer_promotion is not None:
        # Include the claimed offer as a candidate (it may improve at some
        # threshold if it also has a minimum_order_value).
        promo_ids = {p.id for p in all_auto_apply}
        if campaign_offer_promotion.id not in promo_ids:
            all_candidates = [campaign_offer_promotion] + all_auto_apply
        else:
            all_candidates = all_auto_apply
    else:
        all_candidates = all_auto_apply

    # ── Next upgrade ─────────────────────────────────────────────────────────
    transition_points = (
        _collect_transition_points(all_candidates, cart_gross)
        if all_candidates
        else []
    )

    next_upgrade: Optional[OrderDiscountUpgrade] = None

    for tp in transition_points:
        # Evaluate only promotions eligible at this transition point.
        eligible_at_tp = [
            p
            for p in all_candidates
            if p.minimum_order_value is None or tp >= p.minimum_order_value
        ]
        winner_at_tp = _pick_winner(eligible_at_tp, tp)

        if winner_at_tp is None:
            continue

        if current_winner is None:
            # Any winner at tp is a meaningful upgrade over having nothing.
            next_upgrade = OrderDiscountUpgrade(
                threshold=tp,
                remaining=(tp - cart_gross).quantize(_QUANTIZE, ROUND_HALF_UP),
                promotion_name=winner_at_tp.name,
                currency=currency,
            )
            break

        if winner_at_tp.id != current_winner.id:
            # The winner changes — verify the new winner gives the customer
            # strictly more benefit at this cart value.
            current_benefit_at_tp = _compute_gross_discount(current_winner, tp)
            new_benefit_at_tp = _compute_gross_discount(winner_at_tp, tp)
            if new_benefit_at_tp > current_benefit_at_tp:
                next_upgrade = OrderDiscountUpgrade(
                    threshold=tp,
                    remaining=(tp - cart_gross).quantize(_QUANTIZE, ROUND_HALF_UP),
                    promotion_name=winner_at_tp.name,
                    currency=currency,
                )
                break

    return OrderDiscountDecisionState(
        campaign_outcome=campaign_outcome,
        next_upgrade=next_upgrade,
    )
