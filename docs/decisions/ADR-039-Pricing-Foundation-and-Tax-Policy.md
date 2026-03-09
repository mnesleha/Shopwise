# ADR-039: Pricing Foundation and Tax Policy

**Status**: Proposed

**Decision type**: Architecture

**Date**: Sprint 12

## Context

Shopwise is evolving from MVP toward an MMP/1.0-ready e-commerce architecture intended to support not only a single-country storefront, but also future SaaS starter kit / white-label scenarios.

The current pricing model is too limited for this goal:

- products currently store a single price value,
- VAT/tax is not modeled as a first-class concern,
- frontend-facing price presentation is not yet aligned with backend pricing truth,
- future support for multiple countries, multiple tax systems, and multiple currencies would be fragile without a stronger pricing foundation.

The project needs a pricing architecture that:

- supports B2C gross-price presentation,
- keeps backend as the source of truth,
- separates tax calculation from product and promotion logic,
- remains extensible for multiple markets and jurisdictions,
- is understandable and administrable by non-technical business users through admin tooling.

Previous pricing-related decisions already established:

- deterministic snapshot pricing is required for orders,
- frontend must not compute authoritative business pricing,
- rounding behavior must be explicit and centralized.

## Decision

Shopwise adopts a layered pricing foundation with clear separation between:

- base product price storage
- tax calculation
- promotion/discount application
- snapshot pricing for order history

### 1. Product base price storage

Products store their base price as:

- `price_net_amount`
- `currency`
- `tax_class`

The base stored product price is **NET**, not GROSS.

This decision is intentional:

- NET price is more stable for multi-country and multi-tax scenarios,
- GROSS is a derived value that depends on customer/market context,
- tax handling must remain a separate concern from product catalog data.

### 2. Tax as a separate calculation layer

Tax/VAT is not embedded directly into the product price model and is not treated as part of promotion logic.

Instead:

- products reference a `TaxClass`,
- a dedicated tax calculation layer resolves the applicable tax rate based on context,
- the pricing layer produces both NET and GROSS values for presentation and downstream calculations.

This allows future support for:

- country-specific tax rates,
- reduced/zero tax classes,
- tenant-specific tax rules,
- future integration with external tax providers if needed.

### 3. Pricing primitives

Shopwise adopts a money/taxed-money foundation suitable for safe pricing operations.

The preferred implementation direction is to use a pricing library that supports:

- money + currency semantics,
- taxed money representation,
- safe arithmetic and rounding behavior,
- Django model integration where useful.

`django-prices` is approved as the preferred pricing foundation layer for this purpose.

### 4. Frontend presentation

For B2C storefront behavior:

- frontend should typically display **GROSS** prices,
- backend must return enough pricing information for frontend display,
- frontend must not be the authoritative source of tax or discount calculations.

The API should evolve toward returning structured pricing payloads, for example:

- undiscounted price
- discounted price
- tax amount
- currency
- breakdown suitable for B2C display

### 5. Separation of concerns

Pricing architecture must remain split across dedicated responsibilities:

- **Product model** stores the base NET price and tax class.
- **Tax layer** determines applicable tax rules and calculates tax.
- **Promotion layer** applies discount logic to the net price.
- **Pricing service layer** composes the final pricing result.
- **Order snapshot layer** stores final historical prices and tax values.

No single model or table should combine all of these concerns.

### 6. Admin usability

Pricing-related entities must remain manageable for non-technical business users.

This means:

- tax classes must be editable/administerable through Django admin,
- product pricing inputs must remain understandable,
- future promotion management must be business-friendly,
- the architecture must not assume that pricing policy is edited only through code.

## Consequences

**Positive**

- Creates a scalable foundation for multi-country and white-label deployment.
- Keeps tax logic separate from catalog and promotion rules.
- Supports both B2C display needs and accounting-friendly internal modeling.
- Reduces the risk of fragile ad hoc VAT implementations later.
- Makes future pricing services easier to test and evolve.

**Trade-offs**

- Increases upfront modeling complexity compared to a single price field.
- Requires gradual migration of existing catalogue/cart/checkout code.
- Introduces additional service-layer abstractions before all pricing features are fully wired.

## Alternatives Considered

1. Keep a single product price field and calculate VAT ad hoc

   Rejected because it does not scale well to multiple tax systems or currencies and mixes pricing concerns in fragile ways.

2. Store gross price only

   Rejected because gross price is context-dependent and is less suitable as the canonical source for a multi-country pricing model.

3. Store both net and gross as canonical product fields

   Rejected because gross should remain derived from tax policy rather than duplicated as a second source of truth.

4. Handle VAT only at checkout

   Rejected because catalogue and cart pricing already need consistent customer-facing display semantics.

## Notes

This ADR defines the pricing and tax foundation only. It does not yet define:

- promotion model details,
- snapshot field layout in order lines,
- order-level discount allocation,
- external tax provider integration.

Those are handled in follow-up architecture work.
