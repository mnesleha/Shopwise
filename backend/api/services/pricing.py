# api/services/pricing.py
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
        applied_discount: Optional[Discount],
    ):
        self.base_price = base_price          # přesná mezihodnota
        self.final_price = final_price        # ZAOKROUHLENÝ LINE TOTAL
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
    Apply discounts per unit (FIXED wins over PERCENT), then derive line total.
    """

    if quantity <= 0:
        raise InvalidQuantityError("Quantity must be greater than zero")

    if unit_price < ZERO:
        raise InvalidPriceError("Unit price cannot be negative")

    base_price = unit_price * quantity  # pre-discount line price (no rounding)

    valid_fixed = []
    valid_percent = []

    for discount in discounts:
        is_valid = discount.is_valid() if hasattr(discount, "is_valid") else getattr(discount, "is_active", False)
        if not is_valid:
            continue

        if discount.discount_type == Discount.FIXED:
            valid_fixed.append(discount)
        elif discount.discount_type == Discount.PERCENT:
            valid_percent.append(discount)

    applied_discount = valid_fixed[0] if valid_fixed else valid_percent[0] if valid_percent else None

    discounted_unit = unit_price
    if applied_discount:
        if applied_discount.discount_type == Discount.FIXED:
            discounted_unit = unit_price - applied_discount.value
        elif applied_discount.discount_type == Discount.PERCENT:
            discounted_unit = unit_price * (Decimal("1") - applied_discount.value / Decimal("100"))

    if discounted_unit < ZERO:
        discounted_unit = ZERO

    discounted_unit = _round(discounted_unit)
    line_total = _round(discounted_unit * quantity)

    return PricingResult(
        base_price=base_price,
        final_price=line_total,
        applied_discount=applied_discount,
    )
