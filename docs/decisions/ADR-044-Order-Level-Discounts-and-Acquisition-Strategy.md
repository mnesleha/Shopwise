# ADR-044: Order-Level Discounts, Coupon Acquisition Strategy, and VAT-Safe Allocation

**Decision type**: Architecture

**Status**: Proposed

**Date**: Sprint 13

## Context

Shopwise already supports:

- product pricing foundation with net/gross/tax separation,
- line-level promotions,
- checkout pricing authority driven by the backend pricing pipeline,
- order and order-item pricing snapshots,
- invoice-style order detail presentation.

The next architectural gap is order-level discounting and coupon support.

Originally, this was approached as a “coupon field in checkout” problem. However, current UX and conversion best practices indicate that visible promo-code entry mechanisms can trigger friction and FOMO-like discount hunting behavior, which increases abandonment risk. Modern e-commerce patterns instead favor auto-applied discounts, contextual messaging, and campaign-driven application flows where possible.

At the same time, order-level discounts introduce a compliance-sensitive accounting problem:

- invoice data must remain VAT-safe,
- discounts affecting the order total must not remain a purely presentation-level summary deduction,
- order-level discount effects must be allocated into VAT-relevant bases and taxes.

Under EU VAT invoicing rules, invoice data must include, among other things:

- the taxable amount per VAT rate or exemption,
- the unit price exclusive of VAT,
- discounts/rebates if not included in the unit price,
- VAT rate,
- VAT amount payable.

Therefore, order-level discounts must be implemented not merely as a checkout UI feature, but as a pricing/compliance layer with explicit discount acquisition strategy and VAT allocation behavior.

## Decision

Shopwise adopts the following Phase 4 architectural direction:

### 1. Order-level discounting is a first-class pricing layer

Order-level discounts are modeled explicitly and are separate from:

- line-level promotions,
- tax calculation,
- cart/order persistence,
- UI messaging channels.

The pricing stack now consists conceptually of:

1. base product pricing
2. line-level promotions
3. order-level discounts
4. tax calculation / VAT allocation
5. snapshot persistence

### 2. Discount acquisition is modeled before coupon input UX

Shopwise does not treat manual coupon entry as the primary discount journey.

Instead, discount acquisition is modeled through multiple channels, in priority order:

1. on-site automatic application,
2. threshold / progress-based reward unlocking,
3. campaign-driven application (email / URL / UTM / account-bound offers),
4. owned-media product/site messaging,
5. manual code entry as fallback only.

This reflects the principle that discounts should feel like a service, not a scavenger hunt.

### 3. Manual coupon entry is a fallback capability

Manual code entry remains supported, but is not the default or primary checkout interaction model.

It is intended mainly for:

- campaign codes that require explicit entry,
- support-issued vouchers,
- partner / referral / influencer codes,
- future B2B / negotiated-code cases.

### 4. Order-level discount allocation must be VAT-safe

Order-level discounts must be allocated proportionally across VAT-relevant tax bases / VAT buckets.

This allocation must be:

- deterministic,
- auditable,
- rounding-policy-aware,
- persisted in order snapshots.

A pure “minus X in summary” approach is not acceptable as the final accounting model.

### 5. B2C default semantics

For B2C-oriented storefront behavior:

- fixed order-level discounts should be interpreted by default as gross/customer-visible amounts,
- then allocated proportionally into VAT buckets and translated into reduced net base + reduced VAT.

This preserves customer intuition while keeping accounting output consistent.

### 6. Backend remains pricing and accounting authority

The backend determines:

- discount eligibility,
- promotion/coupon resolution,
- order-level allocation,
- resulting VAT breakdown,
- snapshot persistence.

Frontend must not become the authority for:

- discount allocation,
- VAT math,
- accounting interpretation.

### 7. Order detail / invoice remains accounting-first

Any order-level discount that survives into an order must be reflected in:

- VAT breakdown,
- order summary,
- stored snapshots,

not only in customer-facing promotional messaging.

## Consequences

**Positive**

- Aligns coupon/promotions UX with current checkout best practices.
- Reduces FOMO and checkout distraction.
- Creates a scalable acquisition model instead of a single promo-code field.
- Keeps order/invoice output compliance-oriented.
- Makes order-level discount behavior auditable and snapshot-safe.

**Trade-offs**

- Significantly increases architectural complexity compared to “just add coupon field”.
- Requires explicit VAT allocation and rounding policy implementation.
- Requires clear distinction between acquisition channels and accounting effects.
- Increases backend orchestration complexity before frontend simplicity can emerge.

## Alternatives Considered

1. Add a visible coupon field in checkout as the primary entry path

   Rejected because it overemphasizes discount hunting and increases checkout friction.

2. Implement manual coupon entry first, then add auto-apply later

   Rejected because it biases both architecture and UX toward the weakest acquisition pattern.

3. Treat order-level discounts only as summary-level deductions

   Rejected because this is not VAT-safe for invoice/accounting purposes.

4. Delay order-level discounting until after full backoffice UX exists

   Rejected because promotions are a core sales channel and must be architected now, even if backoffice polish comes later.

## Notes

This ADR intentionally does not yet finalize:

- exact coupon lifecycle data model,
- exact allocation residual handling,
- future multiple concurrent coupons,
- full backoffice UX design,
- customer-segment and CRM automation depth.

These belong to follow-up implementation slices.
