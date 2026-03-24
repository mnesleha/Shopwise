# ADR-045: Provider-Agnostic Payment Architecture and Hosted Gateway Integration Strategy

**Decision type**: Architecture

**Status**: Proposed

**Date**: Sprint 15

## Context

Shopwise already supports:

- cart-to-checkout conversion on the backend,
- order creation as a backend-controlled operation,
- order item snapshot persistence,
- inventory reservation during checkout,
- payment as a separate domain concept following order creation,
- frontend checkout flows with payment method selection.

The current checkout flow creates an order in `CREATED` state and defers payment handling to a separate step. This is already directionally compatible with realistic e-commerce payment processing, where the order lifecycle and the payment provider lifecycle are related but not identical.

The next architectural gap is payment provider integration.

Originally, the project used a simple backend-controlled fake payment flow suitable for development. However, the next implementation phase requires integration of a hosted mock payment gateway in order to prepare the system for later integration with real card payment providers.

At the same time, the architecture must avoid coupling checkout behavior directly to a single provider-specific flow. The long-term goal is not merely to add AcquireMock, but to establish a payment architecture where:

- checkout orchestration remains stable,
- payment providers are replaceable,
- provider-specific behavior is isolated,
- backend remains the authority for payment state transitions,
- future real PSP integrations require only limited incremental changes.

This is especially important because hosted checkout providers typically introduce:

- redirect-based customer flows,
- asynchronous webhook confirmation,
- provider-specific payment statuses,
- retry and idempotency concerns,
- delayed finalization relative to checkout submission.

Therefore, payment integration must be designed as an extensible provider architecture rather than as a special-case checkout patch.

## Decision

Shopwise adopts the following architectural direction for payments:

### 1. Payment architecture is provider-agnostic

Payments are modeled as a provider-agnostic domain with explicit separation between:

- customer-facing payment method,
- technical payment provider,
- order lifecycle,
- payment lifecycle,
- provider integration logic.

The system must support multiple payment providers without requiring checkout flow redesign.

### 2. Checkout remains the order creation authority

Checkout remains responsible for:

- validating cart state,
- creating the order,
- creating order items and snapshots,
- reserving inventory,
- converting the cart,
- initiating payment orchestration.

Checkout is not responsible for final payment success determination.

An order is created before external payment confirmation and initially remains in a non-final state.

### 3. Payment result is applied asynchronously and backend-first

Final payment outcome must be determined by backend-controlled payment application logic, not by frontend redirects.

Frontend return/redirect URLs are treated as customer experience steps only.

Backend remains the source of truth for:

- payment success,
- payment failure,
- payment expiration,
- order state transition after payment,
- inventory commitment or release side effects.

### 4. Payment providers are isolated behind a service-layer contract

Provider-specific integration logic must be implemented behind a dedicated provider interface.

This abstraction layer is responsible for:

- starting payment sessions,
- normalizing provider responses,
- verifying webhook authenticity,
- parsing provider events,
- translating provider-specific states into internal payment events.

Provider adapters must not directly mutate order state or inventory state.

### 5. Payment state application is centralized

Payment outcome handling must be centralized in a backend application/service layer that applies normalized payment results to the domain.

This layer is responsible for:

- updating payment records,
- ensuring idempotent transition handling,
- transitioning order state,
- committing inventory reservations on success,
- preserving retry semantics on failure where applicable,
- recording provider payloads for audit/debug purposes.

### 6. Payment method and payment provider are separate concepts

Shopwise explicitly distinguishes:

- **payment method** = the business-facing option selected by the customer (for example `CARD`, `COD`)
- **payment provider** = the technical implementation used to process the payment (for example `DEV_FAKE`, `ACQUIREMOCK`, future real PSPs)

This distinction allows one payment method to be mapped to different providers over time without changing checkout semantics.

### 7. Existing fake payment flow becomes an explicit development provider

The current backend-controlled fake payment flow is retained as an intentional development/testing provider rather than removed.

Its purpose is to provide:

- local development convenience,
- fast backend-driven test scenarios,
- deterministic fallback payment behavior,
- provider abstraction validation before external gateway integration.

This provider is modeled explicitly as `DEV_FAKE`.

### 8. Card payment is introduced through hosted gateway redirect flow

Card payment is introduced through a hosted payment page model.

For the current implementation phase:

- `CARD` is mapped to `ACQUIREMOCK`,
- backend creates the order and starts payment,
- backend returns redirect information,
- frontend redirects the customer to the hosted gateway,
- webhook-driven backend processing finalizes payment,
- frontend return flow only displays the resulting state.

This aligns the architecture with realistic future PSP integration patterns.

### 9. Webhook processing must be idempotent and auditable

Webhook-based payment providers require explicit support for:

- signature verification,
- duplicate event handling,
- safe retries,
- raw payload persistence,
- traceable status transitions.

A repeated provider callback must not cause repeated domain side effects.

### 10. AcquireMock is treated as one provider, not as a permanent architecture dependency

AcquireMock is introduced as a hosted mock gateway provider for development and architecture preparation.

It is not treated as the payment architecture itself.

The architecture must remain open for future providers such as real card gateways without requiring redesign of:

- checkout flow,
- order lifecycle,
- payment state transitions,
- frontend integration contract.

## Consequences

**Positive**

- Establishes a stable payment architecture before real PSP integration.
- Keeps checkout flow intact while allowing richer payment behavior.
- Prevents provider-specific logic from leaking into cart/order domain logic.
- Preserves backend authority over payment and order truth.
- Supports both simple dev flows and realistic hosted gateway flows.
- Reduces future integration cost for real payment providers.
- Improves testability through explicit provider boundaries and normalized events.
- Creates a clean path for webhook/idempotency-safe payment processing.

**Trade-offs**

- Adds architectural complexity compared to a direct fake payment endpoint.
- Requires new abstraction layers and additional payment metadata persistence.
- Introduces asynchronous payment completion semantics into frontend UX.
- Requires webhook verification and idempotency design earlier than a simple MVP would.
- Increases backend orchestration complexity in exchange for long-term extensibility.

## Alternatives Considered

1. Integrate AcquireMock directly into the existing checkout flow as a special case

   Rejected because it would couple checkout behavior to one provider-specific redirect/webhook model and make later real PSP integration more invasive.

2. Keep the current fake payment flow and postpone hosted gateway integration

   Rejected because the project now needs realistic redirect/webhook payment behavior in order to prepare the architecture for real card gateways.

3. Treat frontend redirect completion as payment success

   Rejected because payment truth must come from backend-confirmed provider results, not from customer return navigation.

4. Bind payment method directly to a single provider permanently

   Rejected because payment methods and payment providers evolve independently and must remain separate concepts.

5. Remove the existing fake flow entirely and replace it only with AcquireMock

   Rejected because the fake flow remains valuable as a development/testing provider and as a validation step for the provider abstraction itself.

## Notes

This ADR intentionally does not yet finalize:

- the full detailed payment data model fields,
- the exact provider response DTO shapes,
- retry UX details on the frontend,
- payment expiration policy behavior beyond basic provider mapping,
- future refund/void/partial capture capabilities,
- selection rules for production provider routing,
- final naming of service-layer modules and classes.

These belong to follow-up implementation slices.
