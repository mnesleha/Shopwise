# ADR-043: Order Line Pricing Snapshot Schema

**Decision type**: Architecture

**Status**: Proposed

**Date**: Sprint 12

**Related**: ADR-041, ADR-042, ADR-006, ADR-012, ADR-013

## Context

Order history, auditability, refunds, and future accounting/export integrations require orders to preserve historical pricing truth independently of the current catalogue state.

Previous snapshot decisions established the principle of persisting order-time prices, but the new NET+VAT+promotion pricing model requires a more explicit and richer snapshot structure.

With ADR-042, Shopwise supports **controlled stacking across promotion layers**:

- one winning line promotion,
- one winning order promotion,
- one coupon,

with deterministic application order and compatibility rules.

The snapshot model must therefore preserve not only the final charged totals,
but also enough information to explain how multiple promotion layers contributed
to the final price.

## Decision

### 1. Order Lines Store Explicit Pricing Snapshots

Each `OrderItem` must store explicit order-time pricing values sufficient to reconstruct the final charged amount without consulting live catalogue or promotion tables.

The order line snapshot must include at least:

- `currency`
- `quantity`

#### Base price snapshot

- `base_unit_net_at_order_time`

#### Line-promotion snapshot

- `applied_line_promotion_id` (nullable)
- `applied_line_promotion_name` (nullable)
- `applied_line_promotion_type` (nullable)
- `applied_line_discount_amount_net_per_unit` (nullable)

#### Discounted price snapshot

- `discounted_unit_net_after_line_promotion_at_order_time`

#### Order-level allocation snapshot

If an order-level promotion and/or coupon is applied, its effect must be
allocated across order lines deterministically for historical reconstruction.

- `allocated_order_promotion_id` (nullable)
- `allocated_order_promotion_name` (nullable)
- `allocated_order_promotion_type` (nullable)
- `allocated_order_discount_net_at_order_time` (nullable)

- `allocated_coupon_id` (nullable)
- `allocated_coupon_code` (nullable)
- `allocated_coupon_type` (nullable)
- `allocated_coupon_discount_net_at_order_time` (nullable)

#### Final discounted NET snapshot

- `final_unit_net_at_order_time`

#### Tax snapshot

- `tax_class_code_at_order_time`
- `tax_rate_at_order_time`
- `unit_tax_amount_at_order_time`

#### Gross / totals snapshot

- `unit_gross_at_order_time`
- `line_total_net_at_order_time`
- `line_total_tax_at_order_time`
- `line_total_gross_at_order_time`

#### Explainability / optional snapshot metadata

The implementation may additionally store a tructured JSON explanation payload
for diagnostics and support use cases, for example:

- `pricing_breakdown_json` (optional)

This field is optional and does not replace canonical numeric snapshot fields.

### 2. Order Lines Are the Historical Source of Truth

After checkout completion:

- live catalogue price changes,
- live promotion changes,
- tax configuration changes
- must not affect order history.

Order pricing display must use snapshot fields only.

### 3. Snapshot Write Timing

Snapshot fields are written when the order is created from checkout.

They are immutable afterwards, except for future explicitly modelled refund/accounting extensions.

### 4. Legacy Field Handling

Legacy snapshot fields from older pricing models may be kept temporarily for migration compatibility, but:

- they are not part of the long-term canonical schema,
- they must not be used by new runtime pricing code,
- they should be removed after migration stabilization.

### 5. Order-Level Totals

Order-level totals are derived as the sum of snapped order line totals:

- sum of `line_total_net_at_order_time`
- sum of `line_total_tax_at_order_time`
- sum of `line_total_gross_at_order_time`

The order aggregate must not be recalculated from current product or promotion data.

Order-level promotion and coupon totals must be derivable from the sum of their
line allocations, not from live promotion rules.

### 6. Allocation Rule for Order-Level Discounts

If an order-level promotion or coupon affects the order total, its NET discount
must be allocated to order lines using a deterministic allocation policy.

The exact allocation algorithm is defined by pricing services, but it must:

- be deterministic,
- preserve the exact final order total,
- be reproducible in tests,
- and avoid hidden recalculation from live pricing data.

This rule exists to keep refunds, exports, and audit views line-based and explainable.

## Consequences

**Positive**

- Full historical auditability.
- Safe future support for refunds, exports, and accounting integrations.
- Backend and FE have one authoritative source for order history display.
- Promotion and tax evolution no longer threaten historical consistency.

`Trade-offs`

- More fields on OrderItem.
- Migration/refactor effort is significant.
- Requires careful fixture/test updates.
- Order-level discount allocation introduces additional pricing complexity.

## Guard Rules

- No order history endpoint may derive prices from live product or promotion data.
- Checkout must snapshot final pricing values explicitly.
- Order totals must be based only on order-item snapshots.
- If order-level promotions or coupons are used, their financial effect must be explicitly allocated and snapshotted at line level.
- Optional diagnostic JSON may be added, but canonical historical truth must remain in explicit numeric fields.
