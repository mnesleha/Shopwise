from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional

from discounts.models import Discount
from api.exceptions.pricing import InvalidQuantityError, InvalidPriceError


class PricingResult:
    def __init__(
        self,
        *,
        base_price: Decimal,
        final_price: Decimal,
        unit_price: Decimal,
        applied_discount: Optional[Discount],
    ):
        self.base_price = base_price
        self.final_price = final_price
        self.unit_price = unit_price
        self.applied_discount = applied_discount


ZERO = Decimal("0.00")


def _round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_price(
    *,
    unit_price: Decimal,
    quantity: int,
    discounts: Iterable[Discount],
) -> PricingResult:
    """
    Calculate final price for a cart item.

    Business rules:
    - base price = unit_price * quantity
    - at most one discount is applied
    - FIXED discount has priority over PERCENT
    - discount never produces negative price
    - rounding: ROUND_HALF_UP to 2 decimal places
    """

    if quantity <= 0:
        raise InvalidQuantityError("Quantity must be greater than zero")

    if unit_price < ZERO:
        raise InvalidPriceError("Unit price cannot be negative")

    base_price = unit_price * quantity
    final_price = base_price
    applied_discount = None

    fixed_discount = None
    percent_discount = None

    for discount in discounts:
        if not discount.is_active:
            continue

        if discount.discount_type == Discount.FIXED:
            fixed_discount = discount
        elif discount.discount_type == Discount.PERCENT:
            percent_discount = discount

    if fixed_discount:
        final_price -= fixed_discount.value
        applied_discount = fixed_discount

    elif percent_discount:
        final_price -= (final_price * percent_discount.value / Decimal("100"))
        applied_discount = percent_discount

    if final_price < ZERO:
        final_price = ZERO

    final_price = _round(final_price)

    unit_price = _round(final_price / quantity) if quantity else ZERO

    return PricingResult(
        base_price=(base_price),
        final_price=final_price,
        unit_price=unit_price,
        applied_discount=applied_discount,
    )
