# ADR-041: Pricing Calculation Pipeline and Rounding Policy

**Decision type**: Architecture

**Status**: Proposed

**Date**: Sprint 12

**Related**: ADR-013, ADR-039, ADR-040

## Context

Shopwise is evolving from a simple discount model toward a structured pricing domain with:

- canonical NET prices,
- explicit tax calculation,
- promotion-based discounts,
- and historical pricing snapshots at order level.

Previous pricing decisions established deterministic rounding and snapshot pricing, but they predate the new pricing foundation and do not fully define the end-to-end pricing pipeline once VAT and promotions are introduced.

To avoid divergence between catalogue, cart, checkout, and order snapshot pricing, the system requires one canonical pricing pipeline.

## Decision

### 1. Canonical Pricing Pipeline

All runtime pricing must follow this canonical order:

1. Resolve **base unit NET price**
2. Resolve **_applicable promotions_**
3. Apply promotion discount(s) to unit NET price
4. Produce **discounted unit NET**
5. Resolve **tax rate** from pricing context
6. Calculate **unit tax** from discounted unit NET
7. Produce **unit GROSS**
8. Multiply by quantity to produce line totals
9. Aggregate line totals into cart/order totals

No alternative pricing order is allowed in views, serializers, or frontend code.

### 2. Rounding Policy

Shopwise uses `ROUND_HALF_UP` to 2 decimal places.

Rounding is applied at the following points:

- **discounted unit NET** is rounded to 2 decimals
- **unit tax** is calculated from rounded discounted unit NET and rounded to 2 decimals
- **unit GROSS** = rounded unit NET + rounded unit tax
- **line totals** are calculated from rounded unit values and rounded again to 2 decimals
- **order totals** are the sum of rounded line totals

This means the system is **unit-first, line-second**, not “calculate everything unrounded and round once at the end”.

### 3. Tax Calculation Basis

Tax is always calculated from the **discounted NET amount**, never from the original undiscounted base price.

This ensures:

- discounts reduce taxable base,
- pricing remains accounting-friendly,
- NET remains canonical.

### 4. Backend Authority

The backend pricing service is the only authoritative source of:

- discounted prices,
- tax amounts,
- gross totals,
- order totals.

Frontend may display backend-provided values but must not recalculate authoritative pricing.

### 5. Scope Limitation

This ADR defines the pricing pipeline only.
It does not define:

- promotion stacking/exclusivity rules,
- the exact promotion targeting model,
- the exact order snapshot schema.

Those are covered by follow-up ADRs.

## Consequences

**Positive**

- One deterministic pricing flow across catalogue, cart, checkout, and orders.
- Clear tax calculation semantics.
- Stable foundation for order snapshot pricing.
- Easier FE integration and contract testing.

**Trade-offs**

- Requires refactor of existing pricing helpers and serializer assumptions.
- Existing tests must be updated to reflect unit-first rounding.
- Any shortcut pricing logic outside the pricing service becomes invalid.

## Guard Rules

- No serializer/view may compute prices independently of pricing services.
- No frontend logic may derive final payable totals.
- Tax calculation must always use discounted NET as input.
