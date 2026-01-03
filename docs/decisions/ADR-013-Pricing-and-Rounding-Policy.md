# ADR-013: Pricing and Rounding Policy (Per-Unit Discounts, FIXED Wins)

**Status**: Accepted

**Date**: Sprint 7

**Decision type**: Architecure

## Context

The original pricing implementation applied discounts to line totals (unit_price \* quantity) and performed rounding late in the calculation.

This led to multiple issues:

- Ambiguous semantics of price_at_order_time.
- Counterintuitive behavior for fixed discounts (e.g. FIXED = 150 applied once per line instead of per unit).
- Rounding discrepancies (e.g. 3 × 3.333333 = 9.999999 → 9.99).
- Difficult-to-test pricing logic.
- Frontend uncertainty about how totals were calculated.

Additionally, the system lacked a clear, documented pricing policy suitable for auditability and long-term maintenance.

## Decision

We introduced an explicit and deterministic pricing policy.

### Pricing Rules

1. **All discounts apply per unit**
   - FIXED discounts subtract from each unit price.
   - PERCENT discounts apply to each unit price.
2. **FIXED wins**
   - If any valid FIXED discount exists, PERCENT discounts are ignored.
3. **Non-negative pricing**
   - Discounted unit price is clamped to `>= 0.00`.
4. **Deterministic rounding**
   - Discounted unit price is rounded to 2 decimals using `ROUND_HALF_UP`.
   - Line total is calculated as `rounded_unit_price × quantity`.
   - Line total is rounded again to 2 decimals using `ROUND_HALF_UP`.

### Persistence (Snapshot Strategy)

At checkout time, pricing is snapshotted into `OrderItem`:

- `unit_price_at_order_time`
- `line_total_at_order_time`
- `applied_discount_type_at_order_time`
- `applied_discount_value_at_order_time`

Legacy field `price_at_order_time` is retained temporarily for backward compatibility and stores the line total.

### Principles

- **Predictability**: pricing must be deterministic and testable.
- **Auditability**: orders must explain why a price was charged.
- **Frontend simplicity**: clients never calculate prices.
- **Business intuition**: discounts apply to products, not abstract line sums.
- **Fail-safe design**: prices are never negative.

## Consequences

**Positive**

- Clear and documented pricing semantics.
- Eliminates rounding-related edge cases.
- Enables precise unit and integration testing.
- Supports transparent UI price breakdowns.
- Aligns persistence, business logic, and API representation.

**Negative**

- Change in pricing behavior compared to earlier implementation.
- Required database schema extension (snapshot fields).
- Required refactoring of existing tests and API consumers.
