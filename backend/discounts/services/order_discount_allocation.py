"""Order-level discount VAT allocation engine — Phase 4 / Slice 2.

Responsibility: given a set of priced order lines (after line-level promotions)
and an order-level discount to apply, proportionally allocate the discount
across VAT/tax-rate buckets such that the adjusted tax base, VAT amount and
total-inclusive-VAT per bucket are accounting-correct.

Architectural invariants
------------------------
- Backend is the *sole* pricing/accounting authority.  This engine must never
  be reimplemented or approximated on the frontend.
- Order-level discounts must NOT remain as a bare summary deduction.  They
  must produce per-bucket adjustments that can feed VAT reporting and invoice
  generation.
- Tax is always computed on the *discounted* net (tax base), not the original.

Allocation rule
---------------
Proportional allocation based on bucket gross (post-line-promotion) amounts:

    bucket_share = bucket_gross / total_gross
    bucket_gross_reduction = total_order_discount * bucket_share

Proportional allocation is performed in a single Decimal pass with
ROUND_HALF_UP.  After rounding, a residual (sum of per-bucket reductions may
differ from the target by at most ±1 cent due to rounding) is assigned to the
**largest bucket by gross amount** (stable tie-break by lowest tax_rate).
If zero-gross buckets exist they can never receive a residual.

VAT derivation per bucket
-------------------------
From ``gross_reduction`` per bucket:

    net_reduction  = gross_reduction / (1 + tax_rate / 100)  [ROUND_HALF_UP]
    tax_reduction  = gross_reduction - net_reduction

For zero-rate buckets (tax_rate == 0):
    net_reduction  = gross_reduction
    tax_reduction  = 0

Clamping
--------
No output field is allowed to go negative.  If clamping is required (e.g. a
FIXED discount larger than the total gross) the discount is capped at the
available gross.

Usage
-----
    from discounts.services.order_discount_allocation import (
        OrderDiscountInput,
        OrderLineInput,
        allocate_order_discount,
    )

    lines = [
        OrderLineInput(line_net=Decimal("100.00"), line_gross=Decimal("123.00"),
                       tax_rate=Decimal("23"), currency="EUR"),
        OrderLineInput(line_net=Decimal("50.00"),  line_gross=Decimal("54.00"),
                       tax_rate=Decimal("8"),  currency="EUR"),
    ]
    discount = OrderDiscountInput(type="PERCENT", value=Decimal("10"), currency="EUR")
    result = allocate_order_discount(lines=lines, discount=discount)

    for bucket in result.buckets:
        print(bucket.tax_rate, bucket.adjusted_gross, bucket.adjusted_tax)
    print(result.total_gross_reduction)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Sequence

from discounts.models import PromotionType


_QUANTIZE = Decimal("0.01")
_HUNDRED = Decimal("100")
_ZERO = Decimal("0.00")


def _q(v: Decimal) -> Decimal:
    """Quantise to 2 decimal places using ROUND_HALF_UP."""
    return v.quantize(_QUANTIZE, rounding=ROUND_HALF_UP)


def _clamp_non_negative(v: Decimal) -> Decimal:
    return max(_ZERO, v)


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrderLineInput:
    """Pricing data for a single order line, after line-level promotions.

    The caller is responsible for ensuring these values are already
    post-line-promotion (i.e. as returned by the product/cart pricing pipeline).

    Attributes
    ----------
    line_net:
        Total net amount for this line (unit_net × qty), post-line-promotion.
    line_gross:
        Total gross amount for this line (unit_gross × qty), post-line-promotion.
    tax_rate:
        The tax rate applicable to this line as a percentage (e.g. ``Decimal("23")``
        for 23 %).  Use ``Decimal("0")`` for zero-rated lines.
    currency:
        ISO 4217 currency code.  All lines in a single allocation call must
        share the same currency.
    """

    line_net: Decimal
    line_gross: Decimal
    tax_rate: Decimal
    currency: str


@dataclass(frozen=True)
class OrderDiscountInput:
    """Order-level discount definition to be allocated.

    Attributes
    ----------
    type:
        ``"PERCENT"`` or ``"FIXED"``.
    value:
        Discount magnitude.  For PERCENT: 0 < value ≤ 100.  For FIXED: the
        gross (customer-visible) amount to deduct — B2C default.
    currency:
        ISO 4217 currency code.  Must match the currency of all input lines.
    """

    type: str
    value: Decimal
    currency: str


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrderDiscountBucketResult:
    """Post-allocation pricing breakdown for a single VAT-rate bucket.

    All amounts are in the same currency as the input lines.

    Attributes
    ----------
    tax_rate:
        The VAT rate for this bucket (Decimal percent).
    original_gross:
        Sum of line gross amounts in this bucket (pre-order-discount).
    original_net:
        Sum of line net amounts in this bucket (pre-order-discount).
    original_tax:
        ``original_gross - original_net``.
    gross_reduction:
        The gross discount allocated to this bucket (≥ 0).
    net_reduction:
        Tax-base reduction = ``gross_reduction / (1 + rate/100)`` (≥ 0).
    tax_reduction:
        ``gross_reduction - net_reduction`` (≥ 0).
    adjusted_gross:
        ``original_gross - gross_reduction`` (≥ 0, clamped).
    adjusted_net:
        ``original_net - net_reduction`` (≥ 0, clamped).
    adjusted_tax:
        ``original_tax - tax_reduction`` (≥ 0, clamped).
    """

    tax_rate: Decimal
    original_gross: Decimal
    original_net: Decimal
    original_tax: Decimal
    gross_reduction: Decimal
    net_reduction: Decimal
    tax_reduction: Decimal
    adjusted_gross: Decimal
    adjusted_net: Decimal
    adjusted_tax: Decimal


@dataclass(frozen=True)
class OrderDiscountAllocationResult:
    """Full allocation outcome for an order-level discount.

    Attributes
    ----------
    buckets:
        Per-VAT-rate breakdown.  Ordered by tax_rate ascending.
    total_original_gross:
        Sum of all bucket ``original_gross`` values.
    total_original_net:
        Sum of all bucket ``original_net`` values.
    total_original_tax:
        Sum of all bucket ``original_tax`` values.
    total_gross_reduction:
        Total order-level gross discount actually allocated (≤ order gross;
        equal to sum of bucket ``gross_reduction`` after residual correction).
    total_net_reduction:
        Sum of all bucket ``net_reduction`` values.
    total_tax_reduction:
        Sum of all bucket ``tax_reduction`` values.
    total_adjusted_gross:
        Sum of all bucket ``adjusted_gross`` values.
    total_adjusted_net:
        Sum of all bucket ``adjusted_net`` values.
    total_adjusted_tax:
        Sum of all bucket ``adjusted_tax`` values.
    currency:
        ISO 4217 currency code.
    """

    buckets: List[OrderDiscountBucketResult]
    total_original_gross: Decimal
    total_original_net: Decimal
    total_original_tax: Decimal
    total_gross_reduction: Decimal
    total_net_reduction: Decimal
    total_tax_reduction: Decimal
    total_adjusted_gross: Decimal
    total_adjusted_net: Decimal
    total_adjusted_tax: Decimal
    currency: str


# ---------------------------------------------------------------------------
# Bucket accumulator (internal)
# ---------------------------------------------------------------------------


@dataclass
class _Bucket:
    """Mutable accumulator for lines sharing the same tax_rate."""

    tax_rate: Decimal
    net: Decimal = field(default_factory=lambda: Decimal("0.00"))
    gross: Decimal = field(default_factory=lambda: Decimal("0.00"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def allocate_order_discount(
    *,
    lines: Sequence[OrderLineInput],
    discount: OrderDiscountInput,
) -> OrderDiscountAllocationResult:
    """Allocate an order-level discount proportionally across VAT-rate buckets.

    Parameters
    ----------
    lines:
        Sequence of priced order lines (post-line-promotion).  May share the
        same ``tax_rate``; they will be grouped into buckets.  All lines must
        share the same ``currency``.
    discount:
        The order-level discount to allocate.

    Returns
    -------
    OrderDiscountAllocationResult
        Complete per-bucket and aggregate breakdown.

    Raises
    ------
    ValueError
        If ``lines`` is empty or currencies are inconsistent.
    ValueError
        If ``discount.type`` is not ``"PERCENT"`` or ``"FIXED"``.
    """
    if not lines:
        raise ValueError("lines must not be empty.")

    currency = discount.currency
    for ln in lines:
        if ln.currency != currency:
            raise ValueError(
                f"All lines must share discount currency '{currency}'; "
                f"got '{ln.currency}'."
            )

    if discount.type not in (PromotionType.PERCENT, PromotionType.FIXED):
        raise ValueError(
            f"Unsupported discount type '{discount.type}'. "
            f"Expected 'PERCENT' or 'FIXED'."
        )

    # ------------------------------------------------------------------
    # Step 1: Group lines into VAT-rate buckets.
    # ------------------------------------------------------------------
    bucket_map: Dict[Decimal, _Bucket] = {}
    for ln in lines:
        rate_key = _q(ln.tax_rate)
        if rate_key not in bucket_map:
            bucket_map[rate_key] = _Bucket(tax_rate=rate_key)
        b = bucket_map[rate_key]
        b.net += _q(ln.line_net)
        b.gross += _q(ln.line_gross)

    # Sort buckets by tax_rate ascending for deterministic output ordering.
    sorted_buckets = sorted(bucket_map.values(), key=lambda b: b.tax_rate)

    total_gross = _q(sum(b.gross for b in sorted_buckets))

    # ------------------------------------------------------------------
    # Step 2: Compute total order discount (gross, capped at total_gross).
    # ------------------------------------------------------------------
    if total_gross <= _ZERO:
        # Empty or all-zero gross cart: no discount to allocate.
        total_discount = _ZERO
    elif discount.type == PromotionType.PERCENT:
        total_discount = _q(total_gross * discount.value / _HUNDRED)
    else:
        # FIXED — B2C default: gross amount off, capped at available gross.
        total_discount = _q(min(discount.value, total_gross))

    # ------------------------------------------------------------------
    # Step 3: Proportional allocation.
    #
    # Each bucket gets: total_discount * (bucket_gross / total_gross).
    # We round each share with ROUND_HALF_UP.  Because independent rounding
    # can produce a sum that differs from total_discount by at most
    # ±(n_buckets - 1) cents, we compute the residual and add it to the
    # **largest bucket by gross** (tie-break: lowest tax_rate, already
    # deterministic via sorted order).
    #
    # Buckets with zero gross receive zero allocation and are never chosen
    # for residual assignment.
    # ------------------------------------------------------------------
    if total_discount == _ZERO or total_gross == _ZERO:
        gross_reductions = [_ZERO] * len(sorted_buckets)
    else:
        gross_reductions = []
        for b in sorted_buckets:
            if b.gross <= _ZERO:
                gross_reductions.append(_ZERO)
            else:
                share = _q(total_discount * b.gross / total_gross)
                gross_reductions.append(share)

        # Residual correction.
        allocated_sum = _q(sum(gross_reductions))
        residual = _q(total_discount - allocated_sum)

        if residual != _ZERO:
            # Find the index of the largest-gross non-zero bucket.
            # sorted_buckets is ascending by tax_rate; find max gross among
            # non-zero-gross buckets deterministically (max gross, then first
            # encountered which has lowest tax_rate due to sort order).
            best_idx = max(
                (i for i, b in enumerate(sorted_buckets) if b.gross > _ZERO),
                key=lambda i: sorted_buckets[i].gross,
            )
            gross_reductions[best_idx] = _q(gross_reductions[best_idx] + residual)

    # ------------------------------------------------------------------
    # Step 4: Derive net_reduction and tax_reduction per bucket.
    # Clamp all outputs to ≥ 0.
    # ------------------------------------------------------------------
    result_buckets: List[OrderDiscountBucketResult] = []
    for i, b in enumerate(sorted_buckets):
        gross_red = gross_reductions[i]

        # Cap gross_reduction at bucket gross (guard against floating residual).
        gross_red = _clamp_non_negative(min(gross_red, b.gross))

        rate = b.tax_rate
        if rate == _ZERO:
            # Zero-rate bucket: net == gross, no tax component.
            net_red = gross_red
            tax_red = _ZERO
        else:
            # Back-compute net reduction from the gross reduction.
            # gross = net * (1 + rate/100) → net = gross / (1 + rate/100)
            multiplier = _ZERO + _HUNDRED / (_HUNDRED + rate)
            net_red = _q(gross_red * multiplier)
            tax_red = _clamp_non_negative(_q(gross_red - net_red))

        original_gross = _q(b.gross)
        original_net = _q(b.net)
        original_tax = _clamp_non_negative(_q(original_gross - original_net))

        adjusted_gross = _clamp_non_negative(_q(original_gross - gross_red))
        adjusted_net = _clamp_non_negative(_q(original_net - net_red))
        adjusted_tax = _clamp_non_negative(_q(original_tax - tax_red))

        result_buckets.append(
            OrderDiscountBucketResult(
                tax_rate=rate,
                original_gross=original_gross,
                original_net=original_net,
                original_tax=original_tax,
                gross_reduction=gross_red,
                net_reduction=net_red,
                tax_reduction=tax_red,
                adjusted_gross=adjusted_gross,
                adjusted_net=adjusted_net,
                adjusted_tax=adjusted_tax,
            )
        )

    # ------------------------------------------------------------------
    # Step 5: Aggregate totals.
    # ------------------------------------------------------------------
    def _sum(attr: str) -> Decimal:
        return _q(sum(getattr(rb, attr) for rb in result_buckets))

    return OrderDiscountAllocationResult(
        buckets=result_buckets,
        total_original_gross=_sum("original_gross"),
        total_original_net=_sum("original_net"),
        total_original_tax=_sum("original_tax"),
        total_gross_reduction=_sum("gross_reduction"),
        total_net_reduction=_sum("net_reduction"),
        total_tax_reduction=_sum("tax_reduction"),
        total_adjusted_gross=_sum("adjusted_gross"),
        total_adjusted_net=_sum("adjusted_net"),
        total_adjusted_tax=_sum("adjusted_tax"),
        currency=currency,
    )
