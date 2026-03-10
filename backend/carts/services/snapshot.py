"""Cart item price snapshot helper — Phase 3.

Provides the canonical customer-visible gross unit price to snapshot at
add-to-cart time.

Design notes
------------
- For *migrated* products (``price_net_amount`` is set), the gross price is
  obtained from the pricing pipeline (``get_product_pricing``).  This ensures
  that ``price_at_add_time`` is always a true gross value, inclusive of tax and
  any currently active promotions, instead of a potentially-net legacy price.
- For *unmigrated* products (``price_net_amount`` is ``None``), the function
  falls back to ``product.price``.  The price-change detection service skips
  unmigrated items, so no false-positive comparison will occur.
- ``get_product_pricing`` is imported lazily inside the function to avoid
  introducing a ``carts → products`` module-level import cycle.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from products.models import Product


def get_snapshot_gross_price(product: "Product") -> Decimal:
    """Return the customer-visible gross unit price for a product.

    Called at add-to-cart / PATCH-quantity time to capture
    ``CartItem.price_at_add_time`` as a gross amount, making it a reliable
    baseline for subsequent price-change detection.

    Parameters
    ----------
    product:
        A ``Product`` instance.  If ``price_net_amount`` is set the pricing
        pipeline is invoked; otherwise ``product.price`` is returned.

    Returns
    -------
    Decimal:
        The discounted gross unit price.  This is the amount visible to the
        customer in the catalogue at this instant, after tax and any active
        promotions.  For unmigrated products it is ``product.price`` (legacy
        fallback).
    """
    if product.price_net_amount is not None:
        # Migrated product — resolve the full pricing pipeline to get the
        # customer-visible gross (tax-inclusive, promotion-aware).
        from products.services.pricing import get_product_pricing
        return get_product_pricing(product).discounted.gross.amount
    # Legacy / unmigrated product — price_net_amount not set.  Fall back to
    # product.price.  The price-change detection service will skip this item,
    # so no gross-vs-net comparison will be made.
    return product.price
