ADR-047 Carrier Shipping Architecture with Pluggable Providers and Mock Lifecycle Support

**Decision type**: Architecture

**Status**: Accepted

**Date**: Sprint 15

## Context

Shopwise needs a shipping/delivery subsystem that:

- works end-to-end in local and demo environments without relying on an external carrier,
- is architecturally prepared for later integration with any real shipping provider,
- stays consistent with the existing provider-driven approach already used in payments,
- supports a marketable demo flow, not just backend integration, so shipment lifecycle is visible and presentable.

The shipping flow must align with the current order/payment architecture:

- checkout stores the customer’s shipping selection on `Order`,
- `Shipment` is created only after `Order` reaches final `PAID`,
- shipping lifecycle stays separate from both payment lifecycle and inventory reservation lifecycle,
- the mock provider must support a complete demonstrable lifecycle suitable for video presentation and starterkit showcase.

The system must allow additional providers to be added later without changing checkout flow, order lifecycle, or frontend presentation beyond provider-specific adapter implementation and any optional merchant configuration introduced later.

## Decision

### 1. Shipping is a standalone domain

Shipping is implemented as a standalone subsystem, not as helper logic inside `orders` or `payments`.

Its primary runtime entities are:

- `Shipment`
- `ShipmentEvent`

`Order` remains the business aggregate for the order itself, but it is not the primary source of truth for shipment lifecycle.

### 2. Providers are code-based, not database-driven

Shipping providers are implemented as integration adapters in code, in the same spirit as payment providers.

This means:

- a provider is not modeled as a database table,
- a provider is resolved by `provider_code`,
- every provider implements a shared contract,
- merchant-facing carrier configuration may be added later as a separate layer, but it does not replace the integration adapter.

### 3. Checkout stores shipping selection as an order snapshot

At checkout time, the selected shipping method is stored on `Order` as a snapshot, at minimum:

- `shipping_provider_code`
- `shipping_service_code`
- `shipping_method_name`

This snapshot serves as:

- the source of truth for later shipment creation,
- an audit record of the checkout decision,
- a fallback presentation source on order detail views.

Checkout itself does not create a shipment.

### 4. Shipment is created only after final `PAID`

`Shipment` is created only after the order reaches final `PAID`, through the central application boundary used by payment finalization.

A shipment is not created:

- during checkout,
- during payment session initialization,
- during pending/deferred payment states,
- during redirect initialization.

This ensures that shipping lifecycle begins only after payment has been successfully finalized and inventory reservations have been committed.

### 5. `Shipment` is the primary source of truth for shipping lifecycle

`Shipment.status` is the main shipping truth.

`Order.status` is a secondary business projection of shipment state where that projection is useful.

Minimum mapping:

- `Shipment.IN_TRANSIT` → `Order.SHIPPED`
- `Shipment.DELIVERED` → `Order.DELIVERED`

### 6. Provider events are normalized before persistence

Each provider may produce provider-specific payloads, but shipment creation results, tracking responses, and status events must be normalized before persistence and business processing.

This applies to:

- shipment creation results,
- tracking/status responses,
- webhook or admin-simulated events.

Application services must never depend on raw provider-specific response shapes.

### 7. Admin simulation must go through the service layer

For the mock provider, lifecycle transitions are simulated from Django admin, but admin actions must not mutate shipment or order state directly.

Admin actions must:

- build a normalized shipping event,
- send it through the shipping application/service layer,
- avoid bypassing `ShipmentEvent` persistence or order status projection.

### 8. The mock provider is a first-class provider

The mock provider is not a testing shortcut. It is the first full implementation of the provider contract.

It must support:

- service listing,
- shipment creation,
- tracking/status resolution,
- label generation,
- lifecycle simulation,
- event normalization.

This makes it useful as:

- a local integration provider,
- a demo provider,
- a reference implementation for future real providers.

### 9. The presentation layer consumes summaries, not raw provider payloads

The frontend must not depend on provider-specific payloads or raw `ShipmentEvent` structures.

Instead, it should consume provider-agnostic summary data such as:

- `shipping_method`
- `shipment_summary`
- later `shipment_timeline`

This keeps the UI stable when new providers are added.

## Consequences

### Positive

- A new provider can be added without changing checkout flow or order model.
- The mock provider enables a fully demonstrable end-to-end flow without third-party dependencies.
- The architecture remains consistent with the payments subsystem.
- Shipping lifecycle is auditable through `ShipmentEvent`.
- Frontend presentation can remain stable across provider additions.

### Negative

- Every provider still requires a dedicated adapter implemented in code.
- Merchant-facing carrier configuration is not database-driven in the initial version.
- Event processing and timeline presentation require an application-facing summary layer.
- The mock provider will include demo-oriented capabilities that real providers may not need in the same form.

## Current Implementation

### Domain models

- `Shipment`
- `ShipmentEvent`

### Provider layer

- `BaseShippingProvider`
- `MockShippingProvider`
- provider resolver/registry

### Checkout integration

- checkout validates shipping selection through the provider layer,
- selected shipping method is stored on `Order` as a snapshot.

### Payment integration

- after final `PAID`, shipment is created through a shipping orchestration/service layer,
- shipment creation is idempotent.

### Lifecycle processing

- shipping events are persisted through an application event service,
- duplicate event handling is intentionally conservative:
  - primarily deduplicated by `external_event_id`,
  - fallback deduplication is used only when a sufficiently reliable identifier is present.

### Admin

- mock lifecycle simulation is available from Django admin,
- admin actions go through the shipping service layer.

### Frontend

- checkout sends provider/service codes,
- order detail shows:
  - shipping method,
  - shipment status,
  - tracking number,
  - optional label link when available.

## Canonical Shipping Status Model

The system uses a small set of canonical shipment statuses:

- `PENDING`
- `LABEL_CREATED`
- `IN_TRANSIT`
- `DELIVERED`
- `FAILED_DELIVERY`
- `CANCELLED`

Provider-specific statuses must be mapped to this internal model.

Rules:

- only the provider adapter may know raw provider statuses,
- application services must work only with canonical statuses,
- frontend must receive only canonical or summarized values.

## Rules for Adding a New Provider

A new shipping provider must be added using the following rules.

### 1. Implement a dedicated adapter

Create a new provider adapter, for example:

- `shipping/providers/packeta.py`
- `shipping/providers/dhl.py`

The adapter must implement the `BaseShippingProvider` contract.

### 2. Register the provider in the resolver

The provider must be resolvable through a stable `provider_code`, for example:

- `mock`
- `packeta`
- `dhl`

`provider_code` is a public integration identifier and must not be changed casually after introduction.

### 3. Implement the minimum provider capabilities

Each provider must support, at minimum:

- `list_services(...)`
- `create_shipment(...)`
- `get_tracking_status(...)` or an equivalent status lookup method
- `parse_webhook(...)` or an equivalent event normalization method

If a provider does not natively support one of these capabilities, the adapter must still provide explicit and controlled application behavior.

### 4. Map provider-specific statuses to canonical statuses

The provider adapter is responsible for mapping raw provider statuses to canonical internal statuses.

Application services must never contain:

- provider-specific status mapping branches,
- provider-specific payload parsing logic.

### 5. Do not bypass the shipping service layer

A new provider must not:

- mutate `Shipment` directly outside the service layer,
- mutate `Order.status` directly,
- bypass `ShipmentEvent` persistence.

### 6. Preserve idempotent event processing

If a provider sends asynchronous events or webhooks, the adapter must supply enough information for conservative deduplication:

- ideally `external_event_id`,
- otherwise another trustworthy identifier.

Without a reliable identifier, fallback deduplication must not be aggressive.

### 7. Do not leak provider-specific payloads into the frontend contract

A new provider must not force frontend changes by exposing raw provider payloads.

If UI needs a new value, that value must be added as provider-agnostic summary data.

## Rules for the Mock Provider

The mock provider is designed for development and demo use and must support a complete presentable flow.

### Required capabilities

- shipping service listing
- shipment creation
- tracking number generation
- label generation
- status simulation
- event normalization

### Demo lifecycle

The minimum marketable flow is:

1. `LABEL_CREATED`
2. `IN_TRANSIT`
3. `DELIVERED`

Optional:

- `FAILED_DELIVERY`

### Admin-driven simulation

Simulation is performed from Django admin through the service layer.

### Presentation expectations

The mock provider must enable the team to:

- open a label,
- show shipment timeline,
- show visible status progression,
- inspect shipping history in admin.

## Label Decision

A real mock label is required for a marketable demo.

Decision:

- the mock provider will generate an actual mock shipping label,
- the label will be exposed through shipment summary,
- the label will include at minimum:
  - carrier/service name,
  - receiver,
  - tracking number,
  - order reference,
  - mock QR code or barcode.

## Timeline Decision

A visible shipment timeline is required for a marketable demo.

Decision:

- timeline data will be exposed as backend summary data,
- frontend will not render raw provider payloads,
- polling is intentionally deferred,
- page refresh is acceptable in the initial version.

## Deferred Items

The following are intentionally deferred:

- public tracking page
- realtime polling / websocket refresh
- database-driven merchant carrier configuration
- multi-shipment architecture
- advanced failure/return logistics
- customer notifications
- complex shipping pricing engine

These are not required for the current marketable demo or initial starterkit scope.

## Alternatives Considered and Rejected

### 1. Modeling providers as database records

Rejected because:

- it does not solve integration logic,
- every real provider still needs a dedicated adapter,
- it creates the false impression that providers can be “configured” without code.

### 2. Creating shipments during checkout

Rejected because:

- it does not align with order/payment lifecycle,
- it would create shipments for unpaid orders,
- it would complicate inventory and payment orchestration.

### 3. Updating `Order.status` directly from admin

Rejected because:

- it bypasses shipping truth,
- it loses auditability,
- it is incompatible with future real providers.

### 4. Driving frontend directly from raw shipment events

Rejected because:

- it increases coupling to backend internals,
- it makes provider replacement harder,
- it weakens UI contract stability.

## Recommendations for Future Work

### Short term

- complete mock label generation,
- add frontend shipment timeline,
- improve shipping history readability in Django admin for demo purposes.

### Medium term

- add a second provider as a real-like reference implementation,
- consider merchant-facing `ShippingMethod` configuration,
- consider a public tracking endpoint.

### Long term

- multi-provider merchant configuration,
- pickup point support,
- async refresh/polling,
- return logistics.
