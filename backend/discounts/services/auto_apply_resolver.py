"""Auto-apply order-level promotion resolver — Phase 4 / Slice 3.

Responsibility:
    Given the cart's post-line-promotion gross total, resolve the single
    winning AUTO_APPLY ``OrderPromotion`` — the one the storefront should
    silently apply without any user action required.

Selection algorithm
-------------------
1. Filter: ``acquisition_mode = AUTO_APPLY``, ``is_active = True``,
   within the active time window (``active_from <= now <= active_to``; NULL
   bounds mean "open ended").
2. Eligibility: ``minimum_order_value <= cart_gross``, or
   ``minimum_order_value`` is NULL (always eligible regardless of cart value).
3. Winner: iterate candidates ordered by ``-priority`` then ``id`` (ascending)
   and return the first eligible one.

Only one promotion is returned (the winner).  There is no stacking at the
resolution stage — stacking policy governs how an order-level discount
interacts with *line-level* promotions, which is a concern of the caller.

Returns ``None`` when no AUTO_APPLY promotion is currently eligible.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from discounts.models import AcquisitionMode, OrderPromotion


_QUANTIZE = Decimal("0.01")


@dataclass
class ThresholdRewardProgress:
    """Progress information for a threshold-based AUTO_APPLY order-level reward.

    Attributes
    ----------
    is_unlocked:
        ``True`` when ``current_basis >= threshold``, meaning the promotion has
        been triggered and will be auto-applied by the pricing engine.
    promotion_name:
        Human-readable name of the threshold promotion (for customer messaging).
    threshold:
        Minimum order value (gross, post-line-promotion) required to unlock
        the reward.
    current_basis:
        The cart's qualifying gross total — the same value passed to
        ``resolve_auto_apply_order_promotion``
        (``CartTotalsResult.total_gross``: post-line-discount, pre-order-discount).
    remaining:
        ``max(0, threshold − current_basis)``.  Zero when unlocked.
    currency:
        ISO 4217 currency code for all monetary amounts.
    """

    is_unlocked: bool
    promotion_name: str
    threshold: Decimal
    current_basis: Decimal
    remaining: Decimal
    currency: str


def resolve_auto_apply_order_promotion(
    cart_gross: Decimal,
    currency: str,  # noqa: ARG001  — reserved for future multi-currency filtering
) -> Optional[OrderPromotion]:
    """Return the single winning AUTO_APPLY OrderPromotion for *cart_gross*.

    Parameters
    ----------
    cart_gross:
        Post-line-promotion cart total gross
        (``CartTotalsResult.total_gross.amount``).
    currency:
        ISO 4217 currency of the cart.  Currently unused for filtering
        (the store is assumed single-currency).  Reserved for future use.

    Returns
    -------
    OrderPromotion or None
        The winning promotion, or ``None`` when no AUTO_APPLY promotion is
        eligible for the given cart total.
    """
    now = timezone.now()

    candidates = (
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

    for promotion in candidates:
        min_val = promotion.minimum_order_value
        if min_val is None or cart_gross >= min_val:
            return promotion

    return None


def resolve_threshold_reward_progress(
    cart_gross: Decimal,
    currency: str,
) -> Optional[ThresholdRewardProgress]:
    """Return progress info for the most relevant threshold-based order reward.

    Scans active AUTO_APPLY promotions that have a ``minimum_order_value`` set
    (threshold rewards).  Returns progress data for the most relevant one:

    - If any threshold is already met, returns the highest-priority unlocked
      promotion as ``is_unlocked=True``.
    - Otherwise, returns the promotion closest to being unlocked (smallest
      remaining gap), so the frontend can show an "add X more" message.

    The threshold basis (``current_basis``) is ``cart_gross`` — the same value
    used by :func:`resolve_auto_apply_order_promotion`.  This guarantees
    consistency: when ``is_unlocked`` becomes ``True`` for a given promotion,
    that same promotion will be picked up as the AUTO_APPLY winner and
    reflected in ``CartTotalsResult.order_discount``.

    Parameters
    ----------
    cart_gross:
        Post-line-promotion cart total gross (``CartTotalsResult.total_gross``).
        This is the authoritative threshold basis — the frontend must not
        recompute it.
    currency:
        ISO 4217 currency of the cart.

    Returns
    -------
    ThresholdRewardProgress or None
        Progress info, or ``None`` when no threshold-based AUTO_APPLY
        promotions exist.
    """
    now = timezone.now()

    candidates = list(
        OrderPromotion.objects.filter(
            acquisition_mode=AcquisitionMode.AUTO_APPLY,
            is_active=True,
            minimum_order_value__isnull=False,
        )
        .filter(
            Q(active_from__isnull=True) | Q(active_from__lte=now),
            Q(active_to__isnull=True) | Q(active_to__gte=now),
        )
        .order_by("-priority", "id")
    )

    if not candidates:
        return None

    # Prefer showing an already-unlocked reward (highest priority that is met).
    for promo in candidates:
        min_val = promo.minimum_order_value
        if cart_gross >= min_val:
            return ThresholdRewardProgress(
                is_unlocked=True,
                promotion_name=promo.name,
                threshold=min_val.quantize(_QUANTIZE, ROUND_HALF_UP),
                current_basis=cart_gross.quantize(_QUANTIZE, ROUND_HALF_UP),
                remaining=Decimal("0.00"),
                currency=currency,
            )

    # No threshold met yet — find the promotion with the smallest remaining gap.
    best = min(candidates, key=lambda p: p.minimum_order_value - cart_gross)
    remaining = (best.minimum_order_value - cart_gross).quantize(
        _QUANTIZE, ROUND_HALF_UP
    )
    return ThresholdRewardProgress(
        is_unlocked=False,
        promotion_name=best.name,
        threshold=best.minimum_order_value.quantize(_QUANTIZE, ROUND_HALF_UP),
        current_basis=cart_gross.quantize(_QUANTIZE, ROUND_HALF_UP),
        remaining=remaining,
        currency=currency,
    )
