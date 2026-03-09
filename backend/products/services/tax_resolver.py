"""Tax resolver for Shopwise pricing foundation (Phase 1).

Responsibility: given a net monetary amount, a currency, and an optional
TaxClass, return a ``prices.TaxedMoney`` instance that carries net, gross and
the implicit tax breakdown.

Design decisions
----------------
- The resolver is intentionally dumb: it reads the rate stored on the
  TaxClass and applies it deterministically.  There is no external provider
  call, no tenant logic, and no promotion involvement.
- If the TaxClass has no rate configured (``rate is None``) or no TaxClass is
  supplied at all, the resolver assumes a 0 % tax rate (net == gross).
- The resolver is a stateless function; callers do not need to instantiate
  anything.

Extension point
---------------
Future phases can swap in a provider-based resolver by replacing the call to
``resolve_tax`` with a strategy object.  The signature and return type of
``resolve_tax`` should remain stable.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from prices import Money, TaxedMoney

from products.models import TaxClass


_ZERO_PERCENT = Decimal("0")
_HUNDRED = Decimal("100")
_QUANTIZE = Decimal("0.01")


def _rate_fraction(tax_class: Optional[TaxClass]) -> Decimal:
    """Return the tax rate as a fraction (e.g. 0.23 for 23 %).

    Returns 0 when no TaxClass is supplied or when the rate is not set.
    """
    if tax_class is None or tax_class.rate is None:
        return _ZERO_PERCENT
    return (tax_class.rate / _HUNDRED).quantize(Decimal("0.000001"))


def resolve_tax(
    *,
    net_amount: Decimal,
    currency: str,
    tax_class: Optional[TaxClass] = None,
) -> TaxedMoney:
    """Compute the full tax breakdown for a given net amount.

    Parameters
    ----------
    net_amount:
        The pre-tax monetary amount stored on the product.
    currency:
        ISO 4217 currency code, e.g. ``"EUR"``.
    tax_class:
        The TaxClass assigned to the product.  May be ``None`` if the product
        has no tax class; in that case a 0 % rate is assumed.

    Returns
    -------
    prices.TaxedMoney
        Carries ``.net``, ``.gross``, and ``.tax`` (computed as gross − net).
    """
    rate = _rate_fraction(tax_class)
    net_decimal = net_amount.quantize(_QUANTIZE, rounding=ROUND_HALF_UP)
    gross_decimal = (net_decimal * (1 + rate)).quantize(_QUANTIZE, rounding=ROUND_HALF_UP)

    net_money = Money(net_decimal, currency)
    gross_money = Money(gross_decimal, currency)
    return TaxedMoney(net=net_money, gross=gross_money)
