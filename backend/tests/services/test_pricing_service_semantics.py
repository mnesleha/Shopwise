import pytest
from decimal import Decimal
from discounts.models import Discount
from api.services.pricing import calculate_price


class DummyDiscount:
    """
    Lightweight discount stub for unit-testing pricing logic without DB.
    Must match what pricing service expects: discount_type, value, is_valid().
    """

    def __init__(self, discount_type, value, is_active=True):
        self.discount_type = discount_type
        self.value = Decimal(value)
        self.is_active = is_active

    def is_valid(self):
        return self.is_active


@pytest.mark.parametrize(
    "unit_price, quantity, fixed, percent, expected_total",
    [
        # FIXED per unit: (100 - 150) * 2 => clamp to 0
        ("100.00", 2, "150.00", None, "0.00"),
        # PERCENT per unit: (100 * 0.9) * 2 = 180
        ("100.00", 2, None, "10.00", "180.00"),
        # FIXED wins over PERCENT (still per unit)
        ("100.00", 2, "150.00", "10.00", "0.00"),
    ],
)
def test_discounts_apply_per_unit_fixed_wins(
    unit_price, quantity, fixed, percent, expected_total
):
    discounts = []
    if fixed:
        discounts.append(DummyDiscount(Discount.FIXED, fixed))
    if percent:
        discounts.append(DummyDiscount(Discount.PERCENT, percent))

    result = calculate_price(
        unit_price=Decimal(unit_price),
        quantity=quantity,
        discounts=discounts,
    )

    assert f"{result.final_price:.2f}" == expected_total


def test_unit_price_is_not_mutated_by_quantity():
    """
    Guard test:
    discount must apply per unit, not per line total.
    """
    discounts = [DummyDiscount(Discount.FIXED, "10.00")]

    result = calculate_price(
        unit_price=Decimal("50.00"),
        quantity=3,
        discounts=discounts,
    )

    # (50 - 10) * 3 = 120
    assert f"{result.final_price:.2f}" == "120.00"
