"""Product pricing service for Shopwise (Phase 1 foundation, Phase 2 integration).

Responsibility: compose the full product pricing result from Product model
data, the tax resolver, and (Phase 2) the line-level promotion resolver.
This is the canonical entry-point for catalogue-level pricing; it must be
the *only* place that assembles the final price breakdown.

Phase 2 additions
-----------------
- Line-level promotion resolver integration: discount is applied to NET before
  tax is computed, so tax is always calculated on the post-discount price.
- ``ProductPricingResult`` now carries three tiers:

  * ``undiscounted`` — pricing at full NET (no promotion applied)
  * ``discounted``   — pricing at discounted NET (promotion applied, or equal
                       to undiscounted when no promotion applies)
  * ``discount``     — breakdown of the discount amount (zero when no
                       promotion applies)

Backward compatibility
----------------------
``ProductPricingResult`` exposes convenience ``@property`` shortcuts ``.net``,
``.gross``, ``.tax``, ``.currency``, and ``.tax_rate`` that delegate to the
``discounted`` tier.  Phase 1 consumers (admin code, legacy tests) continue to
work without modification.

Design notes
------------
- Import of the promotion resolver is deferred inside ``get_product_pricing``
  to avoid making ``products.services.pricing`` depend on ``discounts`` at
  module load time.
- The service does not compute tax directly — it delegates to ``resolve_tax``.
- The service does not apply promotions directly — it delegates to
  ``resolve_line_promotion``.

Usage
-----
    from products.services.pricing import get_product_pricing

    result = get_product_pricing(product)
    # Shortcut properties (discounted tier):
    print(result.net)                   # prices.Money — post-discount net
    print(result.gross)                 # prices.Money — post-discount gross
    # Explicit tiers:
    print(result.undiscounted.gross)    # prices.Money — full gross
    print(result.discount.amount_net)   # prices.Money — discount on net
    print(result.discount.promotion_code)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, Optional

from prices import Money, TaxedMoney

from products.services.tax_resolver import resolve_tax

if TYPE_CHECKING:
    from products.models import Product


_QUANTIZE = Decimal("0.01")
_HUNDRED = Decimal("100")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PricingTierResult:
    """Immutable pricing breakdown for a single pricing tier (undiscounted or discounted).

    All monetary values are ``prices.Money`` instances carrying amount + currency.
    """

    net: Money
    gross: Money
    tax: Money
    currency: str
    tax_rate: Decimal


@dataclass(frozen=True)
class DiscountResult:
    """Absolute discount amounts derived from the winning line promotion.

    All monetary fields are zero and code/type are ``None`` when no promotion
    was applied.
    """

    amount_net: Money
    """Discount deducted from the net price (≥ 0)."""

    amount_gross: Money
    """Corresponding gross-equivalent of the discount (undiscounted_gross − discounted_gross)."""

    percentage: Optional[Decimal]
    """Effective percentage discount relative to the undiscounted net price.

    Computed as ``(amount_net / undiscounted_net) * 100``.  ``None`` only when
    the undiscounted net is zero (division by zero guard).
    """

    promotion_code: Optional[str]
    """Stable identifier of the winning promotion, or ``None``."""

    promotion_type: Optional[str]
    """``'PERCENT'`` or ``'FIXED'``, or ``None`` when no promotion applies."""


@dataclass(frozen=True)
class ProductPricingResult:
    """Full promotion-aware pricing breakdown for a single product unit.

    Carries two tiers (undiscounted / discounted) and a discount breakdown.
    When no promotion applies, ``undiscounted`` and ``discounted`` are
    identical and ``discount`` contains all-zero amounts.

    Convenience ``@property`` shortcuts delegate to the *discounted* tier so
    that Phase 1 consumers do not need to be updated:

    - ``result.net``      → ``result.discounted.net``
    - ``result.gross``    → ``result.discounted.gross``
    - ``result.tax``      → ``result.discounted.tax``
    - ``result.currency`` → ``result.discounted.currency``
    - ``result.tax_rate`` → ``result.discounted.tax_rate``
    """

    undiscounted: PricingTierResult
    discounted: PricingTierResult
    discount: DiscountResult

    # ------------------------------------------------------------------
    # Backward-compatible convenience properties (Phase 1 consumers)
    # ------------------------------------------------------------------

    @property
    def net(self) -> Money:
        return self.discounted.net

    @property
    def gross(self) -> Money:
        return self.discounted.gross

    @property
    def tax(self) -> Money:
        return self.discounted.tax

    @property
    def currency(self) -> str:
        return self.discounted.currency

    @property
    def tax_rate(self) -> Decimal:
        return self.discounted.tax_rate

    @classmethod
    def from_taxed_money(
        cls,
        taxed: TaxedMoney,
        *,
        tax_rate: Decimal,
    ) -> "ProductPricingResult":
        """Construct a no-promotion result from a ``prices.TaxedMoney`` instance.

        Kept for backward compatibility with Phase 1 test helpers.  When called
        with no promotion data, ``undiscounted`` and ``discounted`` are the same
        tier and ``discount`` is all-zero.
        """
        tier = PricingTierResult(
            net=taxed.net,
            gross=taxed.gross,
            tax=taxed.tax,
            currency=taxed.net.currency,
            tax_rate=tax_rate,
        )
        zero = Money(Decimal("0.00"), taxed.net.currency)
        return cls(
            undiscounted=tier,
            discounted=tier,
            discount=DiscountResult(
                amount_net=zero,
                amount_gross=zero,
                percentage=Decimal("0"),
                promotion_code=None,
                promotion_type=None,
            ),
        )


# ---------------------------------------------------------------------------
# Service function
# ---------------------------------------------------------------------------


def get_product_pricing(product: "Product") -> Optional[ProductPricingResult]:
    """Return the full promotion-aware pricing breakdown for a product, or ``None``.

    Returns ``None`` when ``product.price_net_amount`` is not set (products not
    yet migrated from the legacy ``price`` field).

    Discount is applied to the NET price first; tax is then computed on the
    post-discount net.  This ensures the tax authority is always the final
    discounted value.

    Parameters
    ----------
    product:
        A ``Product`` instance.  ``tax_class`` and ``category`` are accessed
        via FK; callers should use
        ``select_related("tax_class", "category")`` on the queryset when
        pricing many products at once to avoid N+1 queries.

    Returns
    -------
    ProductPricingResult | None
    """
    if product.price_net_amount is None:
        return None

    currency = product.currency
    tax_class = product.tax_class  # may be None
    tax_rate = tax_class.rate if (tax_class and tax_class.rate is not None) else Decimal("0")

    # Step 1: Compute undiscounted pricing (full net price, no promotion).
    undiscounted_taxed = resolve_tax(
        net_amount=product.price_net_amount,
        currency=currency,
        tax_class=tax_class,
    )
    undiscounted_tier = PricingTierResult(
        net=undiscounted_taxed.net,
        gross=undiscounted_taxed.gross,
        tax=undiscounted_taxed.tax,
        currency=currency,
        tax_rate=tax_rate,
    )

    # Step 2: Resolve line-level promotion (lazy import avoids circular deps).
    from discounts.services.line_promotion import resolve_line_promotion  # noqa: PLC0415

    promo_result = resolve_line_promotion(
        product=product,
        net_amount=product.price_net_amount,
        currency=currency,
    )

    # Step 3: If a promotion applies, compute tax on the discounted NET.
    if promo_result.promotion is None:
        # No promotion — discounted tier == undiscounted tier.
        zero = Money(Decimal("0.00"), currency)
        return ProductPricingResult(
            undiscounted=undiscounted_tier,
            discounted=undiscounted_tier,
            discount=DiscountResult(
                amount_net=zero,
                amount_gross=zero,
                percentage=Decimal("0"),
                promotion_code=None,
                promotion_type=None,
            ),
        )

    discounted_taxed = resolve_tax(
        net_amount=promo_result.discounted_net.amount,
        currency=currency,
        tax_class=tax_class,
    )
    discounted_tier = PricingTierResult(
        net=discounted_taxed.net,
        gross=discounted_taxed.gross,
        tax=discounted_taxed.tax,
        currency=currency,
        tax_rate=tax_rate,
    )

    # Step 4: Discount amounts and percentage.
    amount_net = promo_result.discount_net
    amount_gross = Money(
        (undiscounted_tier.gross.amount - discounted_tier.gross.amount).quantize(
            _QUANTIZE, rounding=ROUND_HALF_UP
        ),
        currency,
    )
    undiscounted_net_amount = undiscounted_tier.net.amount
    if undiscounted_net_amount > 0:
        percentage = (
            amount_net.amount / undiscounted_net_amount * _HUNDRED
        ).quantize(_QUANTIZE, rounding=ROUND_HALF_UP)
    else:
        percentage = None

    return ProductPricingResult(
        undiscounted=undiscounted_tier,
        discounted=discounted_tier,
        discount=DiscountResult(
            amount_net=amount_net,
            amount_gross=amount_gross,
            percentage=percentage,
            promotion_code=promo_result.promotion_code,
            promotion_type=promo_result.promotion_type,
        ),
    )
