"""Cart pricing service for Shopwise Phase 2 / Slice 4.

Responsibility: compose the full cart-level pricing breakdown by applying
the catalogue pricing pipeline (``get_product_pricing``) to every cart item,
then aggregating into cart-level totals.

Design notes
------------
- One DB pass: cart items are fetched with ``select_related`` on
  ``product__tax_class`` and ``product__category``.
- Delegates all per-unit pricing to ``get_product_pricing``; this service
  only orchestrates and aggregates.
- ``get_product_pricing`` is imported lazily inside ``get_cart_pricing`` to
  avoid making ``carts`` depend on ``products`` at module load time.
- Items whose product has no ``price_net_amount`` (not yet migrated from the
  legacy ``price`` field) are included in ``CartTotalsResult.items`` with
  ``unit_pricing=None`` and are excluded from monetary totals.

Usage
-----
    from carts.services.pricing import get_cart_pricing

    result = get_cart_pricing(cart)
    # Per-item:
    for line in result.items:
        print(line.item.product.name, line.unit_pricing)
    # Aggregates:
    print(result.total_gross)   # prices.Money — total after promotions
    print(result.total_discount)
    print(result.total_tax)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, Any, List, Optional

from prices import Money

if TYPE_CHECKING:
    from carts.models import Cart, CartItem
    from products.services.pricing import ProductPricingResult
    from discounts.services.auto_apply_resolver import (
        ThresholdRewardProgress as _ThresholdRewardProgress,
    )


_QUANTIZE = Decimal("0.01")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class OrderDiscountSummary:
    """Summary of the auto-applied order-level discount in a cart pricing result.

    Attributes
    ----------
    gross_reduction:
        Total gross discount amount applied to the cart (≥ 0).
    promotion_code:
        The ``code`` of the applied ``OrderPromotion``.
    promotion_name:
        The human-readable ``name`` of the applied ``OrderPromotion``.
    total_gross_after:
        Cart total gross *after* the order-level discount has been deducted.
    total_tax_after:
        Cart total VAT *after* the order-level discount has been deducted
        (VAT is re-derived proportionally by the allocation engine).
    """

    gross_reduction: Money
    promotion_code: str
    promotion_name: str
    total_gross_after: Money
    total_tax_after: Money


@dataclass
class CartLinePricingResult:
    """Per-line pricing result for a single cart item.

    Attributes
    ----------
    item:
        The ``CartItem`` ORM instance.  ``product``, ``product.tax_class``,
        and ``product.category`` are pre-loaded via ``select_related`` by
        ``get_cart_pricing``.
    quantity:
        Cart item quantity (mirrors ``item.quantity``).
    unit_pricing:
        Full ``ProductPricingResult`` for *one* unit, or ``None`` when the
        product has no ``price_net_amount`` (legacy product).
    """

    item: "CartItem"
    quantity: int
    unit_pricing: Optional["ProductPricingResult"]

    @property
    def item_id(self) -> int:
        return self.item.id

    @property
    def product_id(self) -> int:
        return self.item.product_id


@dataclass
class CartTotalsResult:
    """Aggregated pricing breakdown for an entire cart.

    All monetary totals are computed from the *discounted* per-unit pricing
    multiplied by item quantity — consistent with catalogue pricing where tax
    is always calculated on the post-discount net price.

    ``subtotal_undiscounted`` uses the undiscounted gross so that the UI can
    display the original vs after-promotion subtotals.

    Empty carts (or carts with only unmigrated products) yield all-zero
    totals in the fallback currency (``"EUR"``).
    """

    items: List[CartLinePricingResult]
    """Per-item pricing results in the same order as the DB rows."""

    subtotal_undiscounted: Money
    """sum(undiscounted_gross × qty) — original total before any promotions."""

    subtotal_discounted: Money
    """sum(discounted_gross × qty) — total after promotions; equals ``total_gross``."""

    total_discount: Money
    """``subtotal_undiscounted`` − ``subtotal_discounted`` (≥ 0)."""

    total_tax: Money
    """sum(discounted_tax × qty)."""

    total_gross: Money
    """Total amount payable; equals ``subtotal_discounted``."""

    currency: str
    """ISO 4217 currency code.  Falls back to ``'EUR'`` for empty carts."""

    item_count: int
    """Total units in the cart (sum of quantities), excluding unmigrated lines."""

    order_discount: Optional[OrderDiscountSummary] = field(default=None)
    """Order-level discount resolved from an AUTO_APPLY promotion, or ``None``."""

    threshold_reward: Optional["_ThresholdRewardProgress"] = field(default=None)
    """
    Progress towards a threshold-based AUTO_APPLY reward, or ``None`` when no
    such promotion exists.  Populated by
    :func:`get_cart_pricing_with_order_discount` via
    :func:`~discounts.services.auto_apply_resolver.resolve_threshold_reward_progress`.
    """

    campaign_outcome: Optional[str] = field(default=None)
    """
    Campaign offer outcome when a claimed CAMPAIGN_APPLY offer is present.

    ``"APPLIED"``   — the campaign offer is the current exclusive winner.
    ``"SUPERSEDED"`` — a better auto-apply promotion superseded the offer.
    ``None``         — no campaign offer context.
    """

    order_discount_upgrade: Optional[Any] = field(default=None)
    """
    Next meaningful winner-transition opportunity
    (:class:`~discounts.services.order_discount_decision.OrderDiscountUpgrade`),
    or ``None`` when no better promotion exists at any higher cart value.
    """


# ---------------------------------------------------------------------------
# Service function
# ---------------------------------------------------------------------------


def get_cart_pricing(cart: "Cart") -> CartTotalsResult:
    """Return the full promotion-aware pricing breakdown for a cart.

    Fetches all cart items in a single DB query via ``select_related``, then
    calls ``get_product_pricing`` for each product to build per-line pricing
    and aggregate totals.

    Parameters
    ----------
    cart:
        An active ``Cart`` instance.
    """
    # Lazy import to avoid making carts depend on products at module load time.
    from products.services.pricing import get_product_pricing  # noqa: PLC0415

    items_qs = cart.items.select_related(
        "product__tax_class",
        "product__category",
    ).all()

    line_results: List[CartLinePricingResult] = []
    currency: Optional[str] = None

    # Decimal accumulators — avoid float rounding during summation.
    acc_und = Decimal("0")
    acc_dis = Decimal("0")
    acc_tax = Decimal("0")
    item_count = 0

    for item in items_qs:
        unit_pricing = get_product_pricing(item.product)
        line_results.append(
            CartLinePricingResult(
                item=item,
                quantity=item.quantity,
                unit_pricing=unit_pricing,
            )
        )

        if unit_pricing is None:
            # Product not yet migrated — exclude from monetary totals.
            continue

        qty = Decimal(str(item.quantity))
        if currency is None:
            currency = unit_pricing.currency

        acc_und += unit_pricing.undiscounted.gross.amount * qty
        acc_dis += unit_pricing.discounted.gross.amount * qty
        acc_tax += unit_pricing.discounted.tax.amount * qty
        item_count += item.quantity

    # Safe fallback for empty / fully-unmigrated carts.
    if currency is None:
        currency = "EUR"

    sub_und = Money(acc_und.quantize(_QUANTIZE, ROUND_HALF_UP), currency)
    sub_dis = Money(acc_dis.quantize(_QUANTIZE, ROUND_HALF_UP), currency)
    tot_tax = Money(acc_tax.quantize(_QUANTIZE, ROUND_HALF_UP), currency)
    tot_dis = Money(
        (acc_und - acc_dis).quantize(_QUANTIZE, ROUND_HALF_UP),
        currency,
    )

    return CartTotalsResult(
        items=line_results,
        subtotal_undiscounted=sub_und,
        subtotal_discounted=sub_dis,
        total_discount=tot_dis,
        total_tax=tot_tax,
        total_gross=sub_dis,
        currency=currency,
        item_count=item_count,
    )


def get_cart_pricing_with_order_discount(cart: "Cart") -> CartTotalsResult:
    """Return cart pricing enriched with an auto-applied order-level discount.

    Wraps :func:`get_cart_pricing` and then attempts to resolve an
    ``AUTO_APPLY`` ``OrderPromotion``.  When a promotion wins, the
    ``order_discount`` field on the returned ``CartTotalsResult`` is populated
    with the VAT-correct breakdown; otherwise the result is returned unchanged.

    The cart GET endpoint and the checkout flow should both call this function
    so that the order-level discount is consistently reflected everywhere.

    Parameters
    ----------
    cart:
        An active ``Cart`` instance.
    """
    # Lazy imports to avoid circular dependencies at module load time.
    from discounts.services.auto_apply_resolver import (  # noqa: PLC0415
        resolve_auto_apply_order_promotion,
        resolve_threshold_reward_progress,
    )
    from discounts.services.order_discount_allocation import (  # noqa: PLC0415
        allocate_order_discount,
        OrderDiscountInput,
        OrderLineInput,
    )
    from dataclasses import replace  # noqa: PLC0415

    pricing = get_cart_pricing(cart)

    promotion = resolve_auto_apply_order_promotion(
        cart_gross=pricing.total_gross.amount,
        currency=pricing.currency,
    )

    # Resolve threshold reward progress for all carts — this is always computed
    # using the pre-order-discount total_gross as the authoritative basis.
    threshold_reward = resolve_threshold_reward_progress(
        cart_gross=pricing.total_gross.amount,
        currency=pricing.currency,
    )

    if promotion is None:
        from discounts.services.order_discount_decision import (  # noqa: PLC0415
            resolve_order_discount_decision_state,
        )
        decision = resolve_order_discount_decision_state(
            cart_gross=pricing.total_gross.amount,
            currency=pricing.currency,
            current_winner=None,
        )
        return replace(
            pricing,
            threshold_reward=threshold_reward,
            order_discount_upgrade=decision.next_upgrade,
        )

    # Build per-line inputs for the VAT allocation engine.
    lines = []
    for line in pricing.items:
        if line.unit_pricing is None:
            # Unmigrated product — skip; allocation engine requires proper pricing.
            continue
        qty = Decimal(str(line.quantity))
        lines.append(
            OrderLineInput(
                line_net=(line.unit_pricing.discounted.net.amount * qty).quantize(
                    _QUANTIZE, ROUND_HALF_UP
                ),
                line_gross=(line.unit_pricing.discounted.gross.amount * qty).quantize(
                    _QUANTIZE, ROUND_HALF_UP
                ),
                tax_rate=line.unit_pricing.discounted.tax_rate,
                currency=pricing.currency,
            )
        )

    if not lines:
        # All products are unmigrated — cannot apply order discount.
        from discounts.services.order_discount_decision import (  # noqa: PLC0415
            resolve_order_discount_decision_state,
        )
        decision = resolve_order_discount_decision_state(
            cart_gross=pricing.total_gross.amount,
            currency=pricing.currency,
            current_winner=None,
        )
        return replace(
            pricing,
            threshold_reward=threshold_reward,
            order_discount_upgrade=decision.next_upgrade,
        )

    discount_input = OrderDiscountInput(
        type=promotion.type,
        value=promotion.value,
        currency=pricing.currency,
    )

    allocation = allocate_order_discount(lines=lines, discount=discount_input)

    order_discount = OrderDiscountSummary(
        gross_reduction=Money(
            allocation.total_gross_reduction.quantize(_QUANTIZE, ROUND_HALF_UP),
            pricing.currency,
        ),
        promotion_code=promotion.code,
        promotion_name=promotion.name,
        total_gross_after=Money(
            allocation.total_adjusted_gross.quantize(_QUANTIZE, ROUND_HALF_UP),
            pricing.currency,
        ),
        total_tax_after=Money(
            allocation.total_adjusted_tax.quantize(_QUANTIZE, ROUND_HALF_UP),
            pricing.currency,
        ),
    )

    from discounts.services.order_discount_decision import (  # noqa: PLC0415
        resolve_order_discount_decision_state,
    )
    decision = resolve_order_discount_decision_state(
        cart_gross=pricing.total_gross.amount,
        currency=pricing.currency,
        current_winner=promotion,
    )
    return replace(
        pricing,
        order_discount=order_discount,
        threshold_reward=threshold_reward,
        order_discount_upgrade=decision.next_upgrade,
    )


# ---------------------------------------------------------------------------
# Exclusive promotion winner selection helpers
# ---------------------------------------------------------------------------


def _compute_promotion_gross_discount(promotion: Any, total_gross: Decimal) -> Decimal:
    """Compute the gross discount a promotion would yield on *total_gross*.

    Used to evaluate candidate order-level promotions on the same cart so
    the winner can be selected by highest customer benefit.

    Parameters
    ----------
    promotion:
        An ``OrderPromotion`` instance.
    total_gross:
        Pre-order-discount gross total of the cart (``CartTotalsResult.total_gross``).

    Returns
    -------
    Decimal
        Gross discount amount (≥ 0, ≤ total_gross).
    """
    # Lazy import to avoid a top-level discounts → carts circular path.
    from discounts.models import PromotionType  # noqa: PLC0415

    if total_gross <= Decimal(0):
        return Decimal("0.00")
    if promotion.type == PromotionType.PERCENT:
        return (total_gross * promotion.value / Decimal("100")).quantize(
            _QUANTIZE, ROUND_HALF_UP
        )
    # FIXED — gross-inclusive amount, capped at available gross.
    return min(promotion.value, total_gross).quantize(_QUANTIZE, ROUND_HALF_UP)


def _pick_exclusive_promotion_winner(candidates: list, total_gross: Decimal) -> Any:
    """Return the winning promotion from *candidates* using the EXCLUSIVE rule.

    Selection order — benefit-first (ADR-042 §4.2, benefit-first simplification):

    1. Highest gross benefit evaluated on *total_gross* — the customer always
       gets the largest possible order-level discount.
    2. Highest explicit **priority** — secondary tiebreaker when two promotions
       produce identical gross benefit.
    3. Lowest id — stable deterministic final fallback.

    This ordering is identical to ``resolve_auto_apply_order_promotion`` and
    ``_pick_winner`` in the decision engine, ensuring a single consistent
    winner policy across the whole order-discount subsystem.

    Parameters
    ----------
    candidates:
        Non-empty list of ``OrderPromotion`` instances.
    total_gross:
        Pre-order-discount cart gross used to evaluate each candidate's benefit.

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
            _compute_promotion_gross_discount(p, total_gross),
            p.priority,
            -p.id,  # lower id wins on tie → negate for max()
        ),
    )


def get_cart_pricing_with_campaign_offer(
    cart: "Cart",
    offer: "Any",
) -> CartTotalsResult:
    """Return cart pricing enriched with an EXCLUSIVE order-level promotion.

    Phase 4 / Slice 5B (corrected by exclusive-winner alignment).

    When the session contains a claimed CAMPAIGN_APPLY offer, this function
    selects the **single winning** order-level promotion from:

    - the claimed campaign offer's promotion, and
    - all currently eligible AUTO_APPLY promotions.

    Winner selection uses the EXCLUSIVE rule (ADR-042 §4.2):

    1. Highest gross benefit on the current cart.
    2. Highest explicit ``priority``.
    3. Lowest ``id`` as a stable tie-breaker.

    This guarantees that the customer always receives the best available
    discount and that only one promotion is reflected in the pricing output.

    Parameters
    ----------
    cart:
        An active ``Cart`` instance.
    offer:
        A validated, active ``Offer`` instance whose
        ``promotion.acquisition_mode`` is ``CAMPAIGN_APPLY``.
    """
    # Lazy imports to avoid circular dependencies at module load time.
    from discounts.services.auto_apply_resolver import (  # noqa: PLC0415
        resolve_all_eligible_auto_apply_promotions,
        resolve_threshold_reward_progress,
    )
    from discounts.services.order_discount_allocation import (  # noqa: PLC0415
        allocate_order_discount,
        OrderDiscountInput,
        OrderLineInput,
    )
    from dataclasses import replace as dc_replace  # noqa: PLC0415

    pricing = get_cart_pricing(cart)

    # Threshold reward is always computed from the pre-order-discount total.
    threshold_reward = resolve_threshold_reward_progress(
        cart_gross=pricing.total_gross.amount,
        currency=pricing.currency,
    )

    # Build per-line inputs for the VAT allocation engine.
    lines = []
    for line in pricing.items:
        if line.unit_pricing is None:
            continue
        qty = Decimal(str(line.quantity))
        lines.append(
            OrderLineInput(
                line_net=(line.unit_pricing.discounted.net.amount * qty).quantize(
                    _QUANTIZE, ROUND_HALF_UP
                ),
                line_gross=(line.unit_pricing.discounted.gross.amount * qty).quantize(
                    _QUANTIZE, ROUND_HALF_UP
                ),
                tax_rate=line.unit_pricing.discounted.tax_rate,
                currency=pricing.currency,
            )
        )

    from discounts.services.order_discount_decision import (  # noqa: PLC0415
        resolve_order_discount_decision_state,
    )

    if not lines:
        # All products are unmigrated — cannot apply order discount.
        decision = resolve_order_discount_decision_state(
            cart_gross=pricing.total_gross.amount,
            currency=pricing.currency,
            current_winner=None,
            campaign_offer_promotion=offer.promotion,
        )
        return dc_replace(
            pricing,
            threshold_reward=threshold_reward,
            campaign_outcome=decision.campaign_outcome,
            order_discount_upgrade=decision.next_upgrade,
        )

    # ------------------------------------------------------------------
    # Exclusive winner selection: consider the campaign offer AND all
    # eligible AUTO_APPLY promotions, then pick the one that gives the
    # highest customer benefit.
    # ------------------------------------------------------------------
    auto_apply_candidates = resolve_all_eligible_auto_apply_promotions(
        cart_gross=pricing.total_gross.amount,
        currency=pricing.currency,
    )
    all_candidates = [offer.promotion] + auto_apply_candidates

    winner = _pick_exclusive_promotion_winner(
        all_candidates,
        pricing.total_gross.amount,
    )

    if winner is None:
        decision = resolve_order_discount_decision_state(
            cart_gross=pricing.total_gross.amount,
            currency=pricing.currency,
            current_winner=None,
            campaign_offer_promotion=offer.promotion,
        )
        return dc_replace(
            pricing,
            threshold_reward=threshold_reward,
            campaign_outcome=decision.campaign_outcome,
            order_discount_upgrade=decision.next_upgrade,
        )

    discount_input = OrderDiscountInput(
        type=winner.type,
        value=winner.value,
        currency=pricing.currency,
    )

    allocation = allocate_order_discount(lines=lines, discount=discount_input)

    order_discount = OrderDiscountSummary(
        gross_reduction=Money(
            allocation.total_gross_reduction.quantize(_QUANTIZE, ROUND_HALF_UP),
            pricing.currency,
        ),
        promotion_code=winner.code,
        promotion_name=winner.name,
        total_gross_after=Money(
            allocation.total_adjusted_gross.quantize(_QUANTIZE, ROUND_HALF_UP),
            pricing.currency,
        ),
        total_tax_after=Money(
            allocation.total_adjusted_tax.quantize(_QUANTIZE, ROUND_HALF_UP),
            pricing.currency,
        ),
    )

    decision = resolve_order_discount_decision_state(
        cart_gross=pricing.total_gross.amount,
        currency=pricing.currency,
        current_winner=winner,
        campaign_offer_promotion=offer.promotion,
    )
    return dc_replace(
        pricing,
        order_discount=order_discount,
        threshold_reward=threshold_reward,
        campaign_outcome=decision.campaign_outcome,
        order_discount_upgrade=decision.next_upgrade,
    )
