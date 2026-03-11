"""Checkout price-change detection service — Phase 3 Slice 2.

Responsibility: compare each cart line's ``price_at_add_time`` (the gross
unit price snapshotted when the customer added the item) against the current
effective unit gross produced by the pricing pipeline, and classify any
difference into a severity tier.

Design notes
------------
- Comparison is always gross-vs-gross (customer-visible amounts).
- Unmigrated lines (``unit_pricing is None``) are skipped: no reliable
  comparison basis exists and generating false warnings would be incorrect.
- Severity thresholds are read from Django settings at call time, so tests
  can override them freely via ``@override_settings``.
- No DB writes.  The service is purely computational.

Severity policy
---------------
Given ``p = abs(new - old) / old × 100``:

- ``p <  INFO_THRESHOLD``                              → NONE
- ``INFO_THRESHOLD <= p < WARNING_THRESHOLD``          → INFO
- ``p >= WARNING_THRESHOLD``                           → WARNING

Response shape (``serialize_price_change_summary``)
---------------------------------------------------
::

    {
      "has_changes":    bool,
      "severity":       "NONE" | "INFO" | "WARNING",
      "affected_items": int,
      "items": [
        {
          "product_id":      int,
          "product_name":    str,
          "old_unit_gross":  "100.00",
          "new_unit_gross":  "120.00",
          "absolute_change": "20.00",
          "percent_change":  "20.00",
          "direction":       "UP" | "DOWN",
          "severity":        "INFO" | "WARNING"
        },
        ...
      ]
    }

Only items with severity != NONE appear in the ``items`` list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, List

from django.conf import settings

if TYPE_CHECKING:
    from carts.services.pricing import CartTotalsResult


_QUANTIZE = Decimal("0.01")
_HUNDRED = Decimal("100")
_ZERO = Decimal("0")

_DEFAULT_INFO_THRESHOLD = 1
_DEFAULT_WARN_THRESHOLD = 5


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------


class PriceChangeSeverity:
    NONE = "NONE"
    INFO = "INFO"
    WARNING = "WARNING"


class PriceChangeDirection:
    UP = "UP"
    DOWN = "DOWN"


_SEVERITY_ORDER = {
    PriceChangeSeverity.NONE: 0,
    PriceChangeSeverity.INFO: 1,
    PriceChangeSeverity.WARNING: 2,
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineChangeSummary:
    """Price-change summary for a single cart line.

    Only produced for lines where the price actually changed by a meaningful
    amount (severity != NONE).
    """

    product_id: int
    product_name: str
    old_unit_gross: Decimal   # price_at_add_time
    new_unit_gross: Decimal   # current pipeline discounted gross
    absolute_change: Decimal  # new - old (signed: positive = UP, negative = DOWN)
    percent_change: Decimal   # unsigned percentage relative to old
    direction: str            # UP | DOWN
    severity: str             # INFO | WARNING


@dataclass
class CartPriceChangeSummary:
    """Aggregated price-change report for a full cart checkout.

    ``items`` contains only lines with severity != NONE.
    ``severity`` is the highest severity across all changed lines.
    """

    has_changes: bool
    severity: str           # NONE | INFO | WARNING
    affected_items: int
    items: List[LineChangeSummary] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_thresholds() -> tuple[Decimal, Decimal]:
    """Read threshold settings and return (info, warning) as Decimals.

    Applies defensive normalisation:
    - Negative values fall back to the compiled-in default.
    - When warning < info, warning is raised to match info (non-blocking
      but logged-safe behaviour).
    """
    raw_info = getattr(
        settings,
        "CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT",
        _DEFAULT_INFO_THRESHOLD,
    )
    raw_warn = getattr(
        settings,
        "CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT",
        _DEFAULT_WARN_THRESHOLD,
    )

    info = Decimal(str(raw_info))
    warn = Decimal(str(raw_warn))

    if info < _ZERO:
        info = Decimal(str(_DEFAULT_INFO_THRESHOLD))
    if warn < _ZERO:
        warn = Decimal(str(_DEFAULT_WARN_THRESHOLD))
    if warn < info:
        # Guard: warning threshold must not be below info threshold.
        warn = info

    return info, warn


def _classify(
    percent_change: Decimal,
    info_threshold: Decimal,
    warn_threshold: Decimal,
) -> str:
    """Return severity string for a given unsigned ``percent_change``."""
    if percent_change < info_threshold:
        return PriceChangeSeverity.NONE
    if percent_change < warn_threshold:
        return PriceChangeSeverity.INFO
    return PriceChangeSeverity.WARNING


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_price_changes(cart_pricing: "CartTotalsResult") -> CartPriceChangeSummary:
    """Detect and classify price changes for all cart lines.

    Iterates ``cart_pricing.items`` (a ``CartTotalsResult`` produced by
    ``get_cart_pricing``).  For each *migrated* line, compares the snapshotted
    ``price_at_add_time`` with ``unit_pricing.discounted.gross``.

    Parameters
    ----------
    cart_pricing:
        The full ``CartTotalsResult`` for the cart.  Items must have
        ``item.price_at_add_time`` set (always true for CartItem) and
        ``item.product.name`` accessible (loaded by ``get_cart_pricing``
        via ``select_related``).

    Returns
    -------
    CartPriceChangeSummary
        Always returns a valid summary.  ``has_changes`` is False when no
        line exceeded the info threshold.
    """
    info_t, warn_t = _read_thresholds()

    changed: List[LineChangeSummary] = []
    highest = PriceChangeSeverity.NONE

    for line in cart_pricing.items:
        if line.unit_pricing is None:
            # Unmigrated product — skip; no reliable comparison basis.
            continue

        old_gross = line.item.price_at_add_time.quantize(_QUANTIZE, ROUND_HALF_UP)
        new_gross = line.unit_pricing.discounted.gross.amount.quantize(
            _QUANTIZE, ROUND_HALF_UP
        )

        absolute_change = (new_gross - old_gross).quantize(_QUANTIZE, ROUND_HALF_UP)
        if absolute_change == _ZERO:
            continue

        if old_gross > _ZERO:
            percent_change = (
                abs(absolute_change) / old_gross * _HUNDRED
            ).quantize(_QUANTIZE, ROUND_HALF_UP)
        else:
            # Old price was zero — any non-zero new price is classified as
            # 100 % change so it always reaches at least INFO threshold.
            percent_change = _HUNDRED

        severity = _classify(percent_change, info_t, warn_t)
        if severity == PriceChangeSeverity.NONE:
            continue

        direction = (
            PriceChangeDirection.UP
            if absolute_change > _ZERO
            else PriceChangeDirection.DOWN
        )

        if _SEVERITY_ORDER[severity] > _SEVERITY_ORDER[highest]:
            highest = severity

        changed.append(
            LineChangeSummary(
                product_id=line.item.product_id,
                product_name=line.item.product.name,
                old_unit_gross=old_gross,
                new_unit_gross=new_gross,
                absolute_change=absolute_change,
                percent_change=percent_change,
                direction=direction,
                severity=severity,
            )
        )

    return CartPriceChangeSummary(
        has_changes=bool(changed),
        severity=highest,
        affected_items=len(changed),
        items=changed,
    )


def serialize_price_change_summary(summary: CartPriceChangeSummary) -> dict:
    """Serialise a ``CartPriceChangeSummary`` to a JSON-safe dict.

    This is the canonical shape of the ``price_change`` key in the checkout
    response.  FE consumers must treat this shape as stable.
    """
    return {
        "has_changes": summary.has_changes,
        "severity": summary.severity,
        "affected_items": summary.affected_items,
        "items": [
            {
                "product_id": line.product_id,
                "product_name": line.product_name,
                "old_unit_gross": f"{line.old_unit_gross:.2f}",
                "new_unit_gross": f"{line.new_unit_gross:.2f}",
                "absolute_change": f"{line.absolute_change:.2f}",
                "percent_change": f"{line.percent_change:.2f}",
                "direction": line.direction,
                "severity": line.severity,
            }
            for line in summary.items
        ],
    }
