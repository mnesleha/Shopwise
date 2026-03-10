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

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, List, Optional

from prices import Money

if TYPE_CHECKING:
    from carts.models import Cart, CartItem
    from products.services.pricing import ProductPricingResult


_QUANTIZE = Decimal("0.01")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


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
