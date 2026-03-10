"""Line-level promotion resolver for Shopwise Phase 2.

Responsibility: given a product and its net price context, determine which
single promotion (if any) applies to that line and compute the resulting
discounted net amount.

Phase 2 scope
-------------
- Promotions targeted directly at a product (``PromotionProduct``)
- Promotions targeted at the product's category (``PromotionCategory``)
- Active / date-window filtering
- Single-winner selection: highest priority wins; stable tie-break by
  promotion id (lower id created earlier, deterministic across runs)
- PERCENT and FIXED discount types applied against NET price
- Discounted net is floored at zero (can never go negative)

Not in scope for this slice:
- Tax computation (caller is responsible for applying tax after this step)
- Cart-level or order-level promotions
- Coupon / customer-specific targeting
- Stacking multiple promotions on the same line
- Snapshot persistence

Usage
-----
    from discounts.services.line_promotion import resolve_line_promotion

    result = resolve_line_promotion(
        product=product,
        net_amount=Decimal("49.99"),
        currency="EUR",
    )
    if result.promotion:
        print(result.discounted_net)   # prices.Money
    else:
        print("no promotion applied")
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, Optional

from django.db.models import Q
from django.utils.timezone import now
from prices import Money

from discounts.models import Promotion, PromotionAmountScope, PromotionType

if TYPE_CHECKING:
    from products.models import Product


_QUANTIZE = Decimal("0.01")
_HUNDRED = Decimal("100")
_ZERO = Decimal("0.00")
_ONE = Decimal("1")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinePromotionResult:
    """Immutable output of the line-level promotion resolver.

    Carries enough information for the next pricing layer (tax application,
    serialisation) without coupling to any specific caller.

    Attributes
    ----------
    promotion:
        The winning ``Promotion`` instance, or ``None`` when no promotion
        applies.
    original_net:
        The net price before any discount.
    discount_net:
        The absolute discount amount deducted from the net price (≥ 0).
    discounted_net:
        The net price after discount (≥ 0; never negative).
    currency:
        ISO 4217 currency code taken from the input context.
    promotion_code:
        Shortcut to ``promotion.code`` — ``None`` when no promotion applies.
        Exposed separately so callers do not need to guard against ``None``
        on ``promotion`` just to log the code.
    promotion_type:
        Shortcut to ``promotion.type`` — ``None`` when no promotion applies.
    """

    promotion: Optional[Promotion]
    original_net: Money
    discount_net: Money
    discounted_net: Money
    currency: str
    promotion_code: Optional[str]
    promotion_type: Optional[str]
    amount_scope: Optional[str]
    """'GROSS' or 'NET' for FIXED promotions; ``None`` when no promotion applies."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_within_window(promotion: Promotion) -> bool:
    """Return True when today falls within the promotion's optional date window."""
    today = now().date()
    if promotion.active_from and today < promotion.active_from:
        return False
    if promotion.active_to and today > promotion.active_to:
        return False
    return True


def _compute_discount(
    *,
    promotion: Promotion,
    net_amount: Decimal,
    tax_rate: Decimal = _ZERO,
) -> Decimal:
    """Return the absolute discount amount for *promotion* applied to *net_amount*.

    The result is quantised to 2 decimal places using ROUND_HALF_UP and is
    always clamped to [0, net_amount] so that the discounted net never becomes
    negative.

    For FIXED promotions:
      - ``amount_scope == GROSS`` (default): the fixed value is deducted from
        the gross (customer-visible) price.  The net discount is back-computed
        as ``gross_discount / (1 + tax_rate / 100)``.
      - ``amount_scope == NET``: the fixed value is deducted directly from
        the net (pre-tax) price.
    """
    net_q = net_amount.quantize(_QUANTIZE, rounding=ROUND_HALF_UP)

    if promotion.type == PromotionType.PERCENT:
        raw = (net_amount * promotion.value / _HUNDRED).quantize(
            _QUANTIZE, rounding=ROUND_HALF_UP
        )
    elif promotion.amount_scope == PromotionAmountScope.GROSS:
        # FIXED + GROSS: deduct from the gross price, then back-compute NET discount.
        multiplier = _ONE + tax_rate / _HUNDRED
        undiscounted_gross = (net_amount * multiplier).quantize(
            _QUANTIZE, rounding=ROUND_HALF_UP
        )
        gross_discount = min(
            promotion.value.quantize(_QUANTIZE, rounding=ROUND_HALF_UP),
            undiscounted_gross,
        )
        discounted_gross = undiscounted_gross - gross_discount
        if multiplier > _ZERO:
            discounted_net = (discounted_gross / multiplier).quantize(
                _QUANTIZE, rounding=ROUND_HALF_UP
            )
        else:
            discounted_net = net_q
        raw = net_q - discounted_net
    else:
        # FIXED + NET: deduct from the net price directly.
        raw = promotion.value.quantize(_QUANTIZE, rounding=ROUND_HALF_UP)

    # Clamp to valid range.
    discount = max(_ZERO, min(raw, net_q))
    return discount


def _no_discount_result(*, net_amount: Decimal, currency: str) -> LinePromotionResult:
    """Build a result that represents no promotion being applied."""
    net_money = Money(net_amount.quantize(_QUANTIZE, rounding=ROUND_HALF_UP), currency)
    zero = Money(_ZERO, currency)
    return LinePromotionResult(
        promotion=None,
        original_net=net_money,
        discount_net=zero,
        discounted_net=net_money,
        currency=currency,
        promotion_code=None,
        promotion_type=None,
        amount_scope=None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_line_promotion(
    *,
    product: "Product",
    net_amount: Decimal,
    currency: str,
    tax_rate: Decimal = _ZERO,
) -> LinePromotionResult:
    """Resolve the single winning promotion for a product line.

    Parameters
    ----------
    product:
        The product for which a promotion should be resolved.  ``category``
        is accessed via the FK; callers should use
        ``select_related("category")`` on the queryset when resolving many
        products at once.
    net_amount:
        The product's net (pre-tax) price for this line.
    currency:
        ISO 4217 currency code.  Used to build the monetary output values.
    tax_rate:
        The product's applicable tax rate as a percentage (e.g. ``Decimal("23")``
        for 23 %).  Required for correct FIXED + GROSS discount back-computation;
        defaults to zero (no tax) when omitted.

    Returns
    -------
    LinePromotionResult
        When no applicable promotion is found, ``promotion`` is ``None`` and
        ``discount_net`` is zero (``discounted_net == original_net``).
    """
    today = now().date()

    # Build the targeting filter: promotions that reference this product
    # directly OR that reference the product's category.
    category_id = product.category_id  # None when product has no category

    targeting_q = Q(product_targets__product=product)
    if category_id is not None:
        targeting_q |= Q(category_targets__category_id=category_id)

    # Date-window filter expressed in SQL for efficiency.
    window_q = (
        Q(active_from__isnull=True) | Q(active_from__lte=today)
    ) & (
        Q(active_to__isnull=True) | Q(active_to__gte=today)
    )

    candidates = (
        Promotion.objects.filter(targeting_q, window_q, is_active=True)
        .distinct()
        .order_by("-priority", "id")  # highest priority first; lowest id breaks ties
    )

    winner: Optional[Promotion] = candidates.first()

    if winner is None:
        return _no_discount_result(net_amount=net_amount, currency=currency)

    discount_amount = _compute_discount(
        promotion=winner,
        net_amount=net_amount,
        tax_rate=tax_rate,
    )
    net_q = net_amount.quantize(_QUANTIZE, rounding=ROUND_HALF_UP)
    discounted_amount = net_q - discount_amount

    return LinePromotionResult(
        promotion=winner,
        original_net=Money(net_q, currency),
        discount_net=Money(discount_amount, currency),
        discounted_net=Money(discounted_amount, currency),
        currency=currency,
        promotion_code=winner.code,
        promotion_type=winner.type,
        amount_scope=winner.amount_scope if winner.type == "FIXED" else None,
    )
