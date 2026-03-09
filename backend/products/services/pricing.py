"""Product pricing service for Shopwise Phase 1.

Responsibility: compose the full product pricing result from Product model
data and the tax resolver.  This is the main entry-point for catalogue-level
pricing; it is intentionally not concerned with promotions, cart quantities,
or order snapshots.

Usage
-----
    from products.services.pricing import get_product_pricing

    result = get_product_pricing(product)
    print(result.net)    # prices.Money
    print(result.gross)  # prices.Money
    print(result.tax)    # prices.Money
    print(result.currency)

Design notes
------------
- ``ProductPricingResult`` is a lightweight dataclass; it carries no ORM
  references so it is safe to cache or pass across layer boundaries.
- ``get_product_pricing`` returns ``None`` when the product has no
  ``price_net_amount`` set; callers must handle that case.  This lets the
  function compose cleanly with products that are still being migrated from
  the legacy ``price`` field.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from prices import Money, TaxedMoney

from products.services.tax_resolver import resolve_tax

if TYPE_CHECKING:
    from products.models import Product


@dataclass(frozen=True)
class ProductPricingResult:
    """Immutable pricing breakdown for a single product unit.

    All monetary values are ``prices.Money`` instances, which carry both the
    amount and the currency so they can be formatted or compared safely.
    """

    net: Money
    """Pre-tax unit price."""

    gross: Money
    """Post-tax unit price (net + tax)."""

    tax: Money
    """Tax component (gross − net)."""

    currency: str
    """ISO 4217 currency code."""

    tax_rate: Decimal
    """Applied tax rate as a percentage (e.g. Decimal('23') for 23 %)."""

    @classmethod
    def from_taxed_money(
        cls,
        taxed: TaxedMoney,
        *,
        tax_rate: Decimal,
    ) -> "ProductPricingResult":
        """Construct from a ``prices.TaxedMoney`` instance."""
        return cls(
            net=taxed.net,
            gross=taxed.gross,
            tax=taxed.tax,
            currency=taxed.net.currency,
            tax_rate=tax_rate,
        )


def get_product_pricing(product: "Product") -> Optional[ProductPricingResult]:
    """Return the full pricing breakdown for a product, or ``None``.

    Returns ``None`` when ``product.price_net_amount`` is not set, which
    happens for products not yet migrated to the new pricing model.

    Parameters
    ----------
    product:
        A ``Product`` instance.  ``tax_class`` is accessed via the FK; callers
        should use ``select_related("tax_class")`` on the queryset when pricing
        many products at once.

    Returns
    -------
    ProductPricingResult | None
    """
    if product.price_net_amount is None:
        return None

    tax_class = product.tax_class  # may be None
    tax_rate = tax_class.rate if (tax_class and tax_class.rate is not None) else Decimal("0")

    taxed = resolve_tax(
        net_amount=product.price_net_amount,
        currency=product.currency,
        tax_class=tax_class,
    )

    return ProductPricingResult.from_taxed_money(taxed, tax_rate=tax_rate)
