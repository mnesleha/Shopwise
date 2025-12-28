from decimal import Decimal
from typing import Iterable, Optional

from discounts.models import Discount


class PricingResult:
    def __init__(
        self,
        *,
        base_price: Decimal,
        final_price: Decimal,
        applied_discount: Optional[Discount],
    ):
        self.base_price = base_price
        self.final_price = final_price
        self.applied_discount = applied_discount


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
    raise NotImplementedError
