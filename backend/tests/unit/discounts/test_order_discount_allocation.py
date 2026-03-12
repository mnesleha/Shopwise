"""Unit tests for Phase 4 / Slice 2 — order-level discount VAT allocation engine.

Philosophy: these tests verify accounting correctness and determinism, not
output formatting.  Every test uses Decimal for all monetary values.

Covers:
- Single-rate order with FIXED gross discount
- Single-rate order with PERCENT discount
- Multi-rate order with FIXED gross discount (proportional allocation)
- Multi-rate order with PERCENT discount (proportional allocation)
- Zero-rate bucket behaviour (no tax component)
- Mixed-rate order containing a zero-rate bucket alongside taxed buckets
- Large FIXED discount safely capped at total gross
- FIXED discount exactly equal to total gross (edge: zero adjusted values)
- Deterministic residual allocation — assigned to largest bucket by gross
- Conservation law: sum(bucket.gross_reduction) == total_gross_reduction
- Conservation law after PERCENT: adjusted_gross == original_gross * (1 - pct/100)
- No negative values in any output field under any valid input
- Bucket ordering is ascending by tax_rate
- Currency mismatch raises ValueError
- Empty lines raises ValueError
- Unknown discount type raises ValueError
- Single bucket — full discount goes to that single bucket
- FIXED discount equal to zero produces all-zero reductions
- Multiple lines sharing the same tax_rate are merged into one bucket
"""

from decimal import Decimal

import pytest

from discounts.services.order_discount_allocation import (
    OrderDiscountAllocationResult,
    OrderDiscountBucketResult,
    OrderDiscountInput,
    OrderLineInput,
    allocate_order_discount,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _line(net, gross, rate, currency="EUR") -> OrderLineInput:
    return OrderLineInput(
        line_net=Decimal(str(net)),
        line_gross=Decimal(str(gross)),
        tax_rate=Decimal(str(rate)),
        currency=currency,
    )


def _fixed(value, currency="EUR") -> OrderDiscountInput:
    return OrderDiscountInput(type="FIXED", value=Decimal(str(value)), currency=currency)


def _percent(value, currency="EUR") -> OrderDiscountInput:
    return OrderDiscountInput(type="PERCENT", value=Decimal(str(value)), currency=currency)


def _run(lines, discount) -> OrderDiscountAllocationResult:
    return allocate_order_discount(lines=lines, discount=discount)


# ---------------------------------------------------------------------------
# 1. Single-rate FIXED discount
# ---------------------------------------------------------------------------


def test_single_rate_fixed_gross_discount_basic():
    """net=100, gross=123 (23%), FIXED 23.00 off → bucket gross_red=23.00, net_red=18.70."""
    result = _run(
        lines=[_line(net="100.00", gross="123.00", rate="23")],
        discount=_fixed("23.00"),
    )
    assert len(result.buckets) == 1
    b = result.buckets[0]

    assert b.tax_rate == Decimal("23.00")
    assert b.original_gross == Decimal("123.00")
    assert b.original_net == Decimal("100.00")
    assert b.original_tax == Decimal("23.00")
    assert b.gross_reduction == Decimal("23.00")
    # 23.00 / 1.23 = 18.6991... → ROUND_HALF_UP → 18.70
    assert b.net_reduction == Decimal("18.70")
    # 23.00 - 18.70 = 4.30
    assert b.tax_reduction == Decimal("4.30")
    assert b.adjusted_gross == Decimal("100.00")
    assert b.adjusted_net == Decimal("81.30")
    assert b.adjusted_tax == Decimal("18.70")


def test_single_rate_fixed_aggregates_match_bucket():
    result = _run(
        lines=[_line(net="100.00", gross="123.00", rate="23")],
        discount=_fixed("23.00"),
    )
    assert result.total_original_gross == Decimal("123.00")
    assert result.total_gross_reduction == Decimal("23.00")
    assert result.total_net_reduction == Decimal("18.70")
    assert result.total_tax_reduction == Decimal("4.30")
    assert result.total_adjusted_gross == Decimal("100.00")


# ---------------------------------------------------------------------------
# 2. Single-rate PERCENT discount
# ---------------------------------------------------------------------------


def test_single_rate_percent_10pct():
    """net=100, gross=123 (23%), PERCENT 10% → gross_red=12.30."""
    result = _run(
        lines=[_line(net="100.00", gross="123.00", rate="23")],
        discount=_percent("10"),
    )
    b = result.buckets[0]

    assert b.gross_reduction == Decimal("12.30")
    # 12.30 / 1.23 = 10.00 exactly
    assert b.net_reduction == Decimal("10.00")
    assert b.tax_reduction == Decimal("2.30")
    assert b.adjusted_gross == Decimal("110.70")
    assert b.adjusted_net == Decimal("90.00")
    assert b.adjusted_tax == Decimal("20.70")


def test_single_rate_percent_conservation():
    """sum(adjusted_gross) + total_gross_reduction == total_original_gross."""
    result = _run(
        lines=[_line(net="200.00", gross="246.00", rate="23")],
        discount=_percent("15"),
    )
    lhs = result.total_adjusted_gross + result.total_gross_reduction
    assert lhs == result.total_original_gross


# ---------------------------------------------------------------------------
# 3. Multi-rate FIXED discount — proportional allocation
# ---------------------------------------------------------------------------


def test_multi_rate_fixed_proportional_allocation():
    """Two buckets: 23% (gross=123.00) and 8% (gross=54.00). FIXED 30.00."""
    result = _run(
        lines=[
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="50.00",  gross="54.00",  rate="8"),
        ],
        discount=_fixed("30.00"),
    )
    # total_gross = 177.00
    assert result.total_original_gross == Decimal("177.00")
    assert result.total_gross_reduction == Decimal("30.00")

    b8 = next(b for b in result.buckets if b.tax_rate == Decimal("8"))
    b23 = next(b for b in result.buckets if b.tax_rate == Decimal("23"))

    # 23% share: 30 * 123/177 = 20.847... → 20.85
    assert b23.gross_reduction == Decimal("20.85")
    # 8% share: 30 * 54/177 = 9.152... → 9.15
    assert b8.gross_reduction == Decimal("9.15")

    # Check sum holds after residual correction
    assert b23.gross_reduction + b8.gross_reduction == Decimal("30.00")

    # 23% net_red: 20.85 / 1.23 = 16.9512... → 16.95
    assert b23.net_reduction == Decimal("16.95")
    assert b23.tax_reduction == Decimal("3.90")

    # 8% net_red: 9.15 / 1.08 = 8.4722... → 8.47
    assert b8.net_reduction == Decimal("8.47")
    assert b8.tax_reduction == Decimal("0.68")


def test_multi_rate_fixed_adjusted_values():
    result = _run(
        lines=[
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="50.00",  gross="54.00",  rate="8"),
        ],
        discount=_fixed("30.00"),
    )
    b8 = next(b for b in result.buckets if b.tax_rate == Decimal("8"))
    b23 = next(b for b in result.buckets if b.tax_rate == Decimal("23"))

    assert b23.adjusted_gross == Decimal("102.15")   # 123.00 - 20.85
    assert b8.adjusted_gross == Decimal("44.85")     # 54.00 - 9.15

    total_adj = b23.adjusted_gross + b8.adjusted_gross
    assert total_adj == result.total_adjusted_gross


# ---------------------------------------------------------------------------
# 4. Multi-rate PERCENT discount
# ---------------------------------------------------------------------------


def test_multi_rate_percent_10pct():
    """Two buckets. PERCENT 10% must produce gross_reductions proportional to bucket gross."""
    result = _run(
        lines=[
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="50.00",  gross="54.00",  rate="8"),
        ],
        discount=_percent("10"),
    )
    # total_gross = 177.00, discount = 17.70
    assert result.total_gross_reduction == Decimal("17.70")

    b8 = next(b for b in result.buckets if b.tax_rate == Decimal("8"))
    b23 = next(b for b in result.buckets if b.tax_rate == Decimal("23"))

    # 23%: 17.70 * 123/177 = 12.30 exactly
    assert b23.gross_reduction == Decimal("12.30")
    # 8%: 17.70 * 54/177 = 5.40 exactly
    assert b8.gross_reduction == Decimal("5.40")
    assert b23.gross_reduction + b8.gross_reduction == Decimal("17.70")


def test_multi_rate_percent_conservation():
    """adjusted_gross + gross_reduction == original_gross for each bucket."""
    result = _run(
        lines=[
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="50.00",  gross="54.00",  rate="8"),
        ],
        discount=_percent("10"),
    )
    for b in result.buckets:
        assert b.adjusted_gross + b.gross_reduction == b.original_gross


# ---------------------------------------------------------------------------
# 5. Zero-rate bucket behaviour
# ---------------------------------------------------------------------------


def test_zero_rate_bucket_no_tax_component():
    """Zero-rate lines: tax_reduction must be 0, net_reduction == gross_reduction."""
    result = _run(
        lines=[_line(net="100.00", gross="100.00", rate="0")],
        discount=_percent("10"),
    )
    b = result.buckets[0]

    assert b.tax_rate == Decimal("0")
    assert b.gross_reduction == Decimal("10.00")
    assert b.net_reduction == Decimal("10.00")
    assert b.tax_reduction == Decimal("0.00")
    assert b.original_tax == Decimal("0.00")
    assert b.adjusted_tax == Decimal("0.00")
    assert b.adjusted_net == Decimal("90.00")
    assert b.adjusted_gross == Decimal("90.00")


def test_zero_rate_fixed_discount():
    result = _run(
        lines=[_line(net="50.00", gross="50.00", rate="0")],
        discount=_fixed("10.00"),
    )
    b = result.buckets[0]
    assert b.net_reduction == Decimal("10.00")
    assert b.tax_reduction == Decimal("0.00")
    assert b.adjusted_gross == Decimal("40.00")
    assert b.adjusted_net == Decimal("40.00")


# ---------------------------------------------------------------------------
# 6. Mixed-rate order with zero-rate bucket
# ---------------------------------------------------------------------------


def test_mixed_rate_with_zero_rate_bucket():
    """Zero-rate lines and taxed lines coexist. Proportional allocation still correct."""
    result = _run(
        lines=[
            _line(net="100.00", gross="100.00", rate="0"),
            _line(net="100.00", gross="123.00", rate="23"),
        ],
        discount=_fixed("22.30"),
    )
    # total_gross = 223.00
    assert result.total_original_gross == Decimal("223.00")

    b0 = next(b for b in result.buckets if b.tax_rate == Decimal("0"))
    b23 = next(b for b in result.buckets if b.tax_rate == Decimal("23"))

    # 0% share: 22.30 * 100/223 = 10.0 (exact: 10.0000...)
    # 23% share: 22.30 * 123/223 = 12.3 (exact: 12.3000...)
    assert b0.gross_reduction + b23.gross_reduction == Decimal("22.30")

    # zero-rate bucket: tax_reduction is always 0
    assert b0.tax_reduction == Decimal("0.00")
    assert b0.net_reduction == b0.gross_reduction


# ---------------------------------------------------------------------------
# 7. Large FIXED discount capped at total gross
# ---------------------------------------------------------------------------


def test_fixed_discount_larger_than_total_gross_capped():
    """FIXED 999.99 on a 61.50 gross order → discount capped at 61.50."""
    result = _run(
        lines=[_line(net="50.00", gross="61.50", rate="23")],
        discount=_fixed("999.99"),
    )
    b = result.buckets[0]

    assert b.gross_reduction == Decimal("61.50")
    assert b.adjusted_gross == Decimal("0.00")
    assert b.adjusted_net == Decimal("0.00")
    assert b.adjusted_tax == Decimal("0.00")
    assert result.total_gross_reduction == Decimal("61.50")


def test_fixed_discount_exactly_total_gross_produces_zeros():
    result = _run(
        lines=[_line(net="100.00", gross="108.00", rate="8")],
        discount=_fixed("108.00"),
    )
    b = result.buckets[0]

    assert b.adjusted_gross == Decimal("0.00")
    assert b.adjusted_net == Decimal("0.00")
    assert b.adjusted_tax == Decimal("0.00")


# ---------------------------------------------------------------------------
# 8. Deterministic residual allocation — assigned to largest-gross bucket
# ---------------------------------------------------------------------------


def test_residual_lands_on_largest_bucket():
    """Three equal-gross buckets (33.33 each) with FIXED 10.00.

    proportional: each gets 10 * 33.33/100 = 3.333... rounded to 3.33
    sum = 9.99, residual = 0.01
    Largest gross: tie at 33.33 except bucket 30% has 33.34.
    So bucket 30% (gross=33.34) receives the residual.
    """
    result = _run(
        lines=[
            _line(net="33.33", gross="33.33", rate="0"),
            _line(net="30.30", gross="33.33", rate="10"),
            _line(net="25.65", gross="33.34", rate="30"),
        ],
        discount=_fixed("10.00"),
    )
    b0 = next(b for b in result.buckets if b.tax_rate == Decimal("0"))
    b10 = next(b for b in result.buckets if b.tax_rate == Decimal("10"))
    b30 = next(b for b in result.buckets if b.tax_rate == Decimal("30"))

    assert b0.gross_reduction == Decimal("3.33")
    assert b10.gross_reduction == Decimal("3.33")
    # Largest bucket (33.34) gets the residual → 3.33 + 0.01 = 3.34
    assert b30.gross_reduction == Decimal("3.34")
    assert b0.gross_reduction + b10.gross_reduction + b30.gross_reduction == Decimal("10.00")


def test_residual_tie_break_goes_to_lowest_rate():
    """Three buckets with exactly equal gross: residual goes to the one with lowest tax_rate.

    Because the buckets are ordered ascending by tax_rate and the tie-break for
    max(..., key=bucket.gross) is stable (first encountered = lowest rate), the
    residual lands on the lowest-rate bucket when all bucket gross values are
    identical.
    """
    # Each bucket has gross=100.00; total=300.00; discount=100.00/3 is not representable.
    # FIXED 10.00; each share = 10 * 100/300 = 3.333... → 3.33; residual = 0.01
    result = _run(
        lines=[
            _line(net="100.00", gross="100.00", rate="0"),
            _line(net="90.91", gross="100.00", rate="10"),
            _line(net="83.33", gross="100.00", rate="20"),
        ],
        discount=_fixed("10.00"),
    )
    b0 = next(b for b in result.buckets if b.tax_rate == Decimal("0"))
    b10 = next(b for b in result.buckets if b.tax_rate == Decimal("10"))
    b20 = next(b for b in result.buckets if b.tax_rate == Decimal("20"))

    total_red = b0.gross_reduction + b10.gross_reduction + b20.gross_reduction
    assert total_red == Decimal("10.00")

    # The bucket with the highest gross wins the residual.
    # All three have gross=100.00 (equal). max() is stable → first max = index 0 = rate 0%.
    # So rate 0% gets 3.34, others get 3.33.
    assert b0.gross_reduction == Decimal("3.34")
    assert b10.gross_reduction == Decimal("3.33")
    assert b20.gross_reduction == Decimal("3.33")


# ---------------------------------------------------------------------------
# 9. Conservation laws
# ---------------------------------------------------------------------------


def test_gross_reduction_equals_total_discount_single_rate():
    """For a single-rate order, allocated gross_reduction == requested discount."""
    result = _run(
        lines=[_line(net="200.00", gross="246.00", rate="23")],
        discount=_fixed("50.00"),
    )
    assert result.total_gross_reduction == Decimal("50.00")
    assert result.buckets[0].gross_reduction == Decimal("50.00")


def test_sum_of_bucket_reductions_equals_total_gross_reduction():
    """sum(bucket.gross_reduction) == result.total_gross_reduction for any multi-rate order."""
    result = _run(
        lines=[
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="50.00",  gross="54.00",  rate="8"),
            _line(net="80.00",  gross="80.00",  rate="0"),
        ],
        discount=_percent("12"),
    )
    computed_sum = sum(b.gross_reduction for b in result.buckets)
    assert computed_sum == result.total_gross_reduction


def test_total_adjusted_gross_plus_total_reduction_equals_original():
    """total_adjusted_gross + total_gross_reduction == total_original_gross."""
    result = _run(
        lines=[
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="50.00",  gross="54.00",  rate="8"),
        ],
        discount=_percent("10"),
    )
    assert result.total_adjusted_gross + result.total_gross_reduction == result.total_original_gross


def test_tax_reduction_derivation_per_bucket():
    """tax_reduction == gross_reduction - net_reduction for each bucket."""
    result = _run(
        lines=[
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="50.00",  gross="54.00",  rate="8"),
            _line(net="80.00",  gross="80.00",  rate="0"),
        ],
        discount=_fixed("30.00"),
    )
    for b in result.buckets:
        assert b.tax_reduction == b.gross_reduction - b.net_reduction


# ---------------------------------------------------------------------------
# 10. No negative outputs
# ---------------------------------------------------------------------------


def test_no_negative_adjusted_gross():
    result = _run(
        lines=[_line(net="50.00", gross="61.50", rate="23")],
        discount=_fixed("999.00"),
    )
    for b in result.buckets:
        assert b.adjusted_gross >= Decimal("0.00")
        assert b.adjusted_net >= Decimal("0.00")
        assert b.adjusted_tax >= Decimal("0.00")


def test_no_negative_reductions():
    """All reductions must be ≥ 0 regardless of discount magnitude."""
    result = _run(
        lines=[
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="10.00",  gross="10.80",  rate="8"),
        ],
        discount=_fixed("500.00"),
    )
    for b in result.buckets:
        assert b.gross_reduction >= Decimal("0.00")
        assert b.net_reduction >= Decimal("0.00")
        assert b.tax_reduction >= Decimal("0.00")


def test_no_negative_in_result_totals():
    result = _run(
        lines=[_line(net="100.00", gross="123.00", rate="23")],
        discount=_fixed("999.00"),
    )
    assert result.total_adjusted_gross >= Decimal("0.00")
    assert result.total_adjusted_net >= Decimal("0.00")
    assert result.total_adjusted_tax >= Decimal("0.00")
    assert result.total_gross_reduction >= Decimal("0.00")


# ---------------------------------------------------------------------------
# 11. Bucket ordering is ascending by tax_rate
# ---------------------------------------------------------------------------


def test_buckets_are_ordered_ascending_by_tax_rate():
    result = _run(
        lines=[
            _line(net="50.00",  gross="54.00",  rate="8"),
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="80.00",  gross="80.00",  rate="0"),
        ],
        discount=_percent("5"),
    )
    rates = [b.tax_rate for b in result.buckets]
    assert rates == sorted(rates)


# ---------------------------------------------------------------------------
# 12. Multiple lines sharing the same tax_rate are merged into one bucket
# ---------------------------------------------------------------------------


def test_same_rate_lines_merged_into_one_bucket():
    """Two 23% lines must yield a single bucket, not two."""
    result = _run(
        lines=[
            _line(net="100.00", gross="123.00", rate="23"),
            _line(net="200.00", gross="246.00", rate="23"),
        ],
        discount=_percent("10"),
    )
    assert len(result.buckets) == 1
    b = result.buckets[0]
    assert b.original_gross == Decimal("369.00")  # 123 + 246
    assert b.original_net == Decimal("300.00")    # 100 + 200
    # 10% of 369 = 36.90
    assert b.gross_reduction == Decimal("36.90")


# ---------------------------------------------------------------------------
# 13. Edge: FIXED zero discount produces all-zero reductions
# ---------------------------------------------------------------------------


def test_zero_fixed_discount_no_effect():
    result = _run(
        lines=[_line(net="100.00", gross="123.00", rate="23")],
        discount=_fixed("0.00"),
    )
    b = result.buckets[0]
    assert b.gross_reduction == Decimal("0.00")
    assert b.net_reduction == Decimal("0.00")
    assert b.tax_reduction == Decimal("0.00")
    assert b.adjusted_gross == b.original_gross
    assert b.adjusted_net == b.original_net
    assert b.adjusted_tax == b.original_tax


# ---------------------------------------------------------------------------
# 14. Error handling
# ---------------------------------------------------------------------------


def test_empty_lines_raises():
    with pytest.raises(ValueError, match="lines must not be empty"):
        allocate_order_discount(lines=[], discount=_fixed("10.00"))


def test_currency_mismatch_raises():
    with pytest.raises(ValueError, match="currency"):
        allocate_order_discount(
            lines=[
                _line(net="100.00", gross="123.00", rate="23", currency="EUR"),
                _line(net="50.00",  gross="54.00",  rate="8",  currency="USD"),
            ],
            discount=_fixed("10.00", currency="EUR"),
        )


def test_unknown_discount_type_raises():
    with pytest.raises(ValueError, match="Unsupported discount type"):
        allocate_order_discount(
            lines=[_line(net="100.00", gross="123.00", rate="23")],
            discount=OrderDiscountInput(type="BONUS", value=Decimal("10"), currency="EUR"),
        )


# ---------------------------------------------------------------------------
# 15. Realistic multi-rate scenario end-to-end
# ---------------------------------------------------------------------------


def test_realistic_cart_23_8_0_percent_discount():
    """Grocery-style cart: standard 23%, food 8%, exempt 0%.  PERCENT 10% off."""
    lines = [
        _line(net="100.00", gross="123.00", rate="23"),  # electronics
        _line(net="200.00", gross="216.00", rate="8"),   # food
        _line(net="50.00",  gross="50.00",  rate="0"),   # books (exempt)
    ]
    # total_gross = 389.00
    result = _run(lines=lines, discount=_percent("10"))

    assert result.total_original_gross == Decimal("389.00")
    # 10% of 389.00 = 38.90
    assert result.total_gross_reduction == Decimal("38.90")
    # adjusted total
    assert result.total_adjusted_gross == Decimal("350.10")

    b0 = next(b for b in result.buckets if b.tax_rate == Decimal("0"))
    b8 = next(b for b in result.buckets if b.tax_rate == Decimal("8"))
    b23 = next(b for b in result.buckets if b.tax_rate == Decimal("23"))

    # zero-rate: tax_reduction always 0
    assert b0.tax_reduction == Decimal("0.00")

    # all buckets: gross_reduction = 10% of bucket gross
    assert b0.gross_reduction == Decimal("5.00")    # 10% of 50.00
    assert b8.gross_reduction == Decimal("21.60")   # 10% of 216.00
    assert b23.gross_reduction == Decimal("12.30")  # 10% of 123.00

    # 23% bucket: net_red = 12.30 / 1.23 = 10.00
    assert b23.net_reduction == Decimal("10.00")
    assert b23.tax_reduction == Decimal("2.30")

    # 8% bucket: net_red = 21.60 / 1.08 = 20.00
    assert b8.net_reduction == Decimal("20.00")
    assert b8.tax_reduction == Decimal("1.60")

    # Verify sum of reductions matches
    total_red_check = b0.gross_reduction + b8.gross_reduction + b23.gross_reduction
    assert total_red_check == Decimal("38.90")
