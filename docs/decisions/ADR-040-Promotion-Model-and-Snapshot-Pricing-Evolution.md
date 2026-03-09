# ADR-040: Promotion Model and Snapshot Pricing Evolution

**Status**: Prosposed

**Decision type**: Architecture

**Date**: Sprint 12

## Context

The current discount implementation is based on a discount table that directly couples discount records to products or categories. This approach was acceptable as an early-stage implementation, but it does not scale well for MMP/1.0 goals.

Current pain points:

- discount definition and discount targeting are mixed together,
- promotion administration is difficult for business users,
- concurrent promotions and prioritization are hard to model,
- cart/catalog pricing is tightly coupled to a limited product/category discount model,
- future scenarios such as multiple promotions, category campaigns, or more advanced pricing policies would become increasingly brittle.

At the same time, earlier architecture decisions already established that:

- order pricing must be snapshotted and deterministic,
- historical order values must not change after later catalog/promotion edits,
- frontend must not compute authoritative discount results.

The project now needs a scalable promotion model that:

- separates promotion definition from targeting,
- remains administrable through Django admin,
- works cleanly with the new pricing foundation,
- preserves deterministic snapshots at checkout/order time.

## Decision

Shopwise adopts a promotion-based pricing model with explicit separation between:

- **promotion definition**
- **promotion targeting**
- **runtime pricing calculation**
- **historical snapshot storage**

### 1. Promotion as a first-class domain object

A `Promotion` becomes the canonical definition of a pricing action.

A promotion may define:

- name
- promotion type (`PERCENT`, `FIXED`, later extensible)
- value
- priority
- active window (`active_from`, `active_to`)
- enabled/disabled state
- stacking / exclusivity policy
- optional channel/market scope in the future

The promotion object defines **what the pricing action is**, not **where it applies**.

### 2. Promotion targeting is modeled separately

Promotion targeting must not be modeled by attaching a single discount directly to a product or category.

Instead, targeting is handled through separate relations, for example:

- `PromotionProduct`
- `PromotionCategory`

This allows:

- one promotion to target many products,
- one promotion to target many categories,
- multiple promotions to affect overlapping catalog subsets,
- future extension without redesigning the core promotion object.

### 3. Discounts apply internally to NET price

Promotions/discounts are applied to the **NET** base price.

The tax layer is executed after discount application so that:

- discounted net price becomes the taxable base,
- gross values are derived consistently,
- accounting and multi-country tax logic remain coherent.

Frontend-facing pricing may still display gross discounts and gross totals, but the internal pricing pipeline uses net-first calculation.

### 4. Runtime pricing is calculated by services, not stored in catalog snapshots

Catalogue and cart pricing should be calculated through dedicated pricing services rather than persisted as mutable discount snapshots on catalog objects.

That means:

- catalog pricing is computed on demand,
- cart pricing is computed by service logic using current pricing rules,
- promotion application is deterministic and centralized,
- product-level “discount snapshots” are not used as the canonical long-term model.

### 5. Historical pricing is snapshotted at order line level

Final authoritative historical pricing must be stored at the order line level.

Order line snapshots should eventually include:

- unit net before discount
- unit net after discount
- tax amount
- unit gross
- currency
- applied promotion identifiers or snapshot references
- any necessary rounded line totals

This ensures:

- historical order values do not change if product prices or promotions later change,
- auditability is preserved,
- checkout/order behavior remains deterministic.

### 6. Existing discount model is transitional

The existing direct discount model is considered a transitional implementation and will be evolved toward the promotion architecture described here.

Existing discount behavior should not be expanded further unless needed for backward compatibility during migration.

### 7. Admin usability is a first-class requirement

Promotion architecture must be designed to be manageable by business users in Django admin.

This means:

- promotion definition must be understandable without code changes,
- target assignment must be manageable in admin workflows,
- priority and active windows must be visible and editable,
- the architecture should support future custom admin UI, but must already be operable in Django admin.

## Consequences

**Positive**

- Separates concerns cleanly between pricing definition, targeting, calculation, and history.
- Supports future scalability for white-label and multi-market scenarios.
- Makes promotion administration more realistic for business users.
- Avoids locking the product model into rigid one-discount assumptions.
- Aligns with snapshot pricing requirements for orders.

**Trade-offs**

- Requires migration away from the existing discount model.
- Introduces more pricing domain objects than the current MVP implementation.
- Requires explicit promotion priority/stacking policy decisions.
- Cart and checkout pricing wiring will need staged migration.

## Alternatives Considered

1. Keep direct product/category discount records as the main model

   Rejected because it mixes promotion definition with targeting and does not scale well.

2. Add `discount_id` directly to product/category

   Rejected because it still assumes an overly rigid relationship and does not handle overlapping promotions well.

3. Build a full visual business-rules engine now

   Rejected because it adds too much complexity too early, and many candidate libraries are not maintainable or actively supported.

4. Snapshot discounts directly into catalog/cart records as the long-term model

   Rejected because catalog/cart pricing is runtime pricing, while durable historical truth belongs in order lines.

## Notes

This ADR does not yet finalize:

- exact promotion stacking policy,
- line-level vs order-level promotion allocation rules,
- admin UX customization beyond Django admin basics,
- migration sequence for replacing the existing discount model in checkout/cart code.

Those are intentionally left to follow-up implementation planning.
