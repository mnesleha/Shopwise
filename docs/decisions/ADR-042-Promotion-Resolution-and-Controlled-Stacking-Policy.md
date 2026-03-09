# ADR-042: Promotion Resolution and Controlled Stacking Policy

**Decision type**: Architecture

**Status**: Proposed

**Date**: Sprint 12

**Related**: ADR-039, ADR-040, ADR-041, ADR-043

## Context

Shopwise is evolving from MVP toward **MMP (Minimal Marketable Product)**. In this phase, promotions are no longer treated as a future enhancement but as a core commercial capability that directly affects conversion and marketability.

ADR-040 establishes promotions as first-class pricing objects and separates:

- promotion definition,
- targeting,
- runtime resolution,
- and historical snapshots.

However, implementation cannot proceed safely until the system explicitly defines:

- which promotions may combine,
- how conflicting promotions are resolved,
- how deterministic pricing is preserved,
- and how the pricing engine avoids uncontrolled combinatorial complexity.

The system must therefore support **controlled stacking**, not unlimited stacking and not oversimplified “single winner only” pricing.

## Decision

### 1. Promotion Layers

Promotions are resolved in distinct layers:

1. **Line Promotion**
   - applies to individual order lines
   - typically product-targeted or category-targeted

2. **Order Promotion**
   - applies to the order/cart subtotal
   - typically threshold-based or cart-level campaign logic

3. **Coupon / Voucher**
   - explicitly entered by the user
   - may apply to the order or eligible lines depending on definition

Shipping promotions are **out of scope** for this ADR and require a future ADR.

### 2. Controlled Stacking Model

Shopwise supports **controlled stacking across layers**, with the following rules:

- At most **one winning Line Promotion** may apply to a given line
- At most **one winning Order Promotion** may apply to the order
- At most **one Coupon** may apply to the order

Promotions may stack **across layers** only if they are compatible.

This means the system may produce combinations such as:

- 1× Line Promotion
  - 1× Order Promotion
  - 1× Coupon

…but never multiple winners within the same layer.

### 3. Exclusivity and Compatibility

Each promotion defines whether it is:

- **exclusive** – blocks other promotions outside allowed exceptions
- **stackable** – may be combined with compatible promotions in other layers

Compatibility is governed by the following rules:

- If a promotion is marked **exclusive**, it blocks any other promotion unless the other promotion is explicitly allowed by future policy.
- If a coupon is marked non-combinable, it must not stack with another order-level promotion.
- Line promotions do not stack with other line promotions on the same line.

This keeps pricing deterministic and prevents uncontrolled promotion overlap.

### 4. Intra-Layer Resolution

If multiple eligible promotions exist in the same layer, the pricing engine selects **one winner** using deterministic resolution.

#### 4.1 Line Promotion winner

For each line, choose the eligible promotion that produces the **lowest discounted unit NET**.

Tie-breaker order:

1. higher explicit promotion priority
2. product-targeted promotion over category-targeted promotion
3. fixed-amount discount over percentage discount
4. lower promotion ID as final deterministic fallback

#### 4.2 Order Promotion winner

For the order as a whole, choose the eligible order-level promotion that produces the **lowest final order NET subtotal** after line promotions have been applied.

Tie-breaker order:

1. higher explicit promotion priority
2. fixed-amount discount over percentage discount
3. lower promotion ID

#### 4.3 Coupon winner

Only one coupon may be active at a time.
If multiple coupon candidates are possible in the future, the same deterministic tie-breaker policy must apply.

### 5. Canonical Application Order

Promotion resolution must follow this order:

1. Resolve base unit NET prices
2. Resolve and apply the winning **Line Promotion** per line
3. Produce discounted line NET values
4. Aggregate subtotal
5. Resolve and apply the winning **Order Promotion**
6. Resolve and apply the **Coupon**, if present and compatible
7. Pass the discounted NET result into tax calculation
8. Produce final gross totals
9. Write explicit pricing snapshots

Tax is always calculated **after** promotion discounts, in line with ADR-039/041 pricing principles.

### 6. Backend-Only Resolution

Promotion resolution is performed only by a dedicated backend pricing/promotion resolver.

It must not be duplicated in:

- serializers
- views
- admin forms
- frontend code

Frontend consumes already-resolved pricing and promotion summary data.

### 7. Scope for MMP / v1.0

This ADR supports the following MMP scope:

- line promotions
- order promotions
- one coupon
- controlled stacking across layers
- exclusivity flag
- deterministic tie-breakers
- snapshot of applied promotion effects

The following are explicitly out of scope for now:

- multiple simultaneous coupons
- multiple stacked line promotions on the same line
- shipping promotions
- buy-X-get-Y
- customer-segment combinatorics beyond current eligibility model
- arbitrary rule engine behavior

Those require future ADRs.

## Consequences

**Positive**

- Promotions become commercially useful for MMP, not merely technically present.
- The pricing engine remains deterministic and testable.
- The model supports common real-world e-commerce scenarios without opening unlimited complexity.
- Snapshot pricing remains auditable and explainable.

**Trade-offs**

- The pricing engine becomes more complex than a single-winner MVP model.
- More snapshot detail and test coverage are required.
- Admin/business rules must clearly communicate exclusivity and compatibility behavior.

## Guard Rules

- Promotions may stack **only across approved layers**, never aritrarily.
- At most one winner exists per promotion layer.
- Promotion exclusivity must be explicit and centrally enforced.
- Promotion resolution must be deterministic and backend-owned.
- Any new promotion type or stacking dimension requires a new ADR.

## Follow-ups

This ADR requires the following implementation-aligned decisions and artifacts:

- explicit pricing pipeline and rounding policy (ADR-041)
- explicit order pricing snapshot schema (ADR-043)
- promotion eligibility and targeting implementation details
- comprehensive pricing and promotion test matrix
