import pytest
from decimal import Decimal
from api.services.pricing import calculate_price


class DummyDiscount:
    def __init__(self, kind, value, is_active=True):
        self.kind = kind
        self.value = Decimal(value)
        self.is_active = is_active


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
        discounts.append(DummyDiscount("FIXED", fixed))
    if percent:
        discounts.append(DummyDiscount("PERCENT", percent))

    result = calculate_price(Decimal(unit_price), quantity, discounts)

    assert f"{result.final_price:.2f}" == expected_total


def test_unit_price_is_not_mutated_by_quantity():
    """
    Guard test:
    quantity must NOT influence how discount is applied to unit price.
    """
    discounts = [DummyDiscount("FIXED", "10.00")]

    result = calculate_price(Decimal("50.00"), 3, discounts)

    # (50 - 10) * 3 = 120
    assert f"{result.final_price:.2f}" == "120.00"
