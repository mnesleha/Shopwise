# ADR-045: Provider-Agnostic Payments Architecture and Hosted Gateway Integration

**Decision type**: Architecture

**Status**: Accepted

**Date**: Sprint 15

## Context

Shopwise already had a checkout flow where:

- the backend creates the order,
- order items and pricing snapshots are persisted at checkout - time,
- inventory is reserved during checkout,
- payment is modeled as a separate concern after order creation.

This baseline made it possible to introduce card payments without redesigning the cart/order domain. The architectural goal was not only to integrate AcquireMock as a development gateway, but to establish a payment architecture that is:

- provider-agnostic,
- backend-authoritative,
- compatible with both direct and hosted redirect flows,
- extensible toward future real payment providers.

At the same time, the implementation had to preserve a development-friendly payment path and avoid coupling checkout/order logic directly to one provider’s API conventions.

During implementation, several practical architectural decisions were required beyond the original proposal:

- separation of business-facing `payment_method` from technical `provider`,
- centralization of payment side effects into one application layer,
- redirect-session initiation for hosted providers without prematurely finalizing payment,
- webhook-finalized truth for hosted card payments,
- provider-owned callback URL composition,
- frontend redirect/return handling based only on normalized backend semantics.

The result is no longer just a target architecture proposal; it is the implemented payment architecture used by Shopwise today. The earlier backend foundation PR introduced the provider-agnostic payment model, provider contract, resolver, orchestration layer, centralized result applier, and preservation of the DEV fake payment path. That foundation explicitly aimed to keep public API behavior stable while preparing the system for real provider integration.

## Decision

Shopwise adopts the following implemented payments architecture:

### 1. Checkout remains the order creation authority

Checkout is responsible for:

- validating cart state,
- creating the order,
- creating order items and snapshots,
- reserving inventory,
- converting the cart,
- invoking payment orchestration after order creation.

Checkout is not responsible for determining final payment success.

An order is created before payment confirmation. For hosted providers, order finalization happens later via webhook-confirmed payment outcome.

### 2. Payment method and payment provider are separate concepts

Shopwise explicitly distinguishes:

- **payment method** = the business-facing option selected by the customer (`CARD`, `COD`)
- **payment provider** = the technical implementation used to process the payment (`ACQUIREMOCK`, `DEV_FAKE`)

This separation is persisted on the `Payment` model and used throughout orchestration and provider resolution.

This means that:

- frontend and checkout speak in customer/business terms,
- payment infrastructure speaks in provider terms,
- future provider replacement does not require redesign of payment method semantics.

### 3. Payment orchestration is centralized in the backend

All payment initiation flows go through a backend orchestration layer.

This orchestration layer is responsible for:

- resolving the provider from the selected payment method,
- creating the `Payment` record in `PENDING`,
- invoking the provider through a shared contract,
- delegating result application to a centralized payment result applier.

Checkout, order services, and frontend do not call provider APIs directly.

### 4. Providers are isolated behind a shared contract

All providers implement a shared provider boundary consisting of:

- a provider start context,
- a normalized provider result,
- a common start operation.

The provider layer is responsible only for:

- calling the external/mock payment system,
- returning normalized initiation/result data,
- exposing provider-specific technical details inside the payments layer.

Providers do not directly mutate order state, inventory state, or other cart/order domain objects.

### 5. Payment side effects are centralized in one application path

Payment and order state transitions are applied centrally through the payment result application layer.

This layer is the only place where:

- `Payment` status changes are persisted,
- `paid_at`, `failed_at`, `failure_reason`, `provider_payment_id`, and `redirect_url` are stored,
- order finalization is applied,
- inventory reservation side effects are committed on successful payment.

This preserves domain consistency and prevents provider-specific ad hoc state mutation.

### 6. Hosted redirect providers are initiation-first, not success-first

For hosted payment providers, starting the payment session is explicitly not treated as successful payment completion.

In Shopwise:

- a hosted provider session start may return `success=True` as a technical initiation result,
- but if the result includes a redirect URL, the payment remains `PENDING`,
- the order remains in its non-final state,
- inventory reservations remain only reserved, not committed.

Final success or failure for hosted providers is applied only after webhook confirmation.

This prevents false-positive `PAID` orders at checkout time.

### 7. Webhook-confirmed backend truth is the source of final payment state

For hosted card payment flows, final payment truth is determined by backend webhook processing.

Shopwise therefore treats:

- frontend redirect/return as UX only,
- webhook-confirmed provider outcome as the authoritative payment result.

AcquireMock webhook handling includes:

- HMAC signature verification,
- fail-closed behavior for missing webhook secret,
- payload normalization,
- explicit status mapping,
- pragmatic idempotence,
- delegated application through the existing centralized payment result path.

Repeated deliveries must not duplicate side effects.

### 8. DEV fake payment flow remains supported as a provider

The pre-existing backend-controlled development payment flow is retained and modeled explicitly as a technical provider (`DEV_FAKE`).

This preserves:

- local development convenience,
- simplified test flows,
- deterministic backend-driven scenarios,
- a stable non-hosted direct payment path for development use.

This provider remains useful even after hosted gateway integration.

### 9. CARD currently maps to a hosted provider; COD remains direct/deferred dev-compatible

The currently implemented provider routing is:

- `CARD -> ACQUIREMOCK`
- `COD -> DEV_FAKE`

`CARD` behaves as a hosted redirect flow:

- checkout creates order,
- orchestration creates payment,
- provider starts hosted session,
- frontend redirects,
- webhook finalizes payment/order.

`COD` currently remains a direct/deferred dev-compatible flow through `DEV_FAKE`.

This means COD is architecturally provider-based, but its business semantics remain intentionally development-oriented rather than a finalized production cash-on-delivery workflow.

### 10. Provider-specific callback composition belongs to the payments layer

Checkout no longer composes provider-specific callback URLs.

Instead:

- checkout passes only generic callback/base context,
- the hosted provider implementation composes its own callback URLs inside the payments layer.

This removes the last provider-specific callback leak from the checkout entrypoint and ensures that adding a new hosted provider does not require checkout view changes merely because of callback wiring.

### 11. Frontend remains provider-agnostic and non-authoritative

The frontend is responsible only for:

- sending `payment_method`,
- interpreting normalized checkout payment initiation data,
- redirecting for hosted flows,
- rendering post-return payment state based on backend truth.

Frontend must not:

- know provider-specific internals,
- derive payment success from browser return alone,
- become the authority for payment completion.

The frontend return flow therefore reads backend order/payment truth after gateway return and renders:

- pending,
- success,
- failure

based on backend state.

### 12. New hosted providers should now be a payments-layer change

After the callback-composition cleanup, adding a new hosted provider under an existing business-facing payment method should require changes primarily in:

- provider implementation,
- provider enum/config,
- resolver mapping,
- provider-specific webhook handling inside the payments/API layer.

It should not require changes to checkout view/domain logic merely to support provider callback URLs.

If a completely new business-facing payment method is introduced, API/schema/frontend updates are still expected. That is considered a business contract change, not a provider-boundary failure.

## Consequences

**Positive**

- Keeps checkout and order creation stable while supporting realistic payment provider behavior.
- Establishes a provider-agnostic payment architecture usable for future real PSP integrations.
- Keeps backend as the source of truth for final payment state.
- Prevents false payment success during hosted session creation.
- Preserves strong boundaries between cart/order domain and provider-specific code.
- Supports both direct/development and hosted/redirect provider patterns.
- Keeps frontend thin and provider-agnostic.
- Makes adding another hosted provider significantly more localized.

**Trade-offs**

- Introduces more layers than a simple fake payment endpoint.
- Requires asynchronous mental model for hosted payment flows.
- Adds webhook handling, signature verification, and idempotence earlier than a minimal MVP would.
- Keeps COD semantics development-oriented for now rather than product-final.
- `provider_reference` exists in the model but is not currently required for the implemented AcquireMock flow, because webhook matching uses `provider_payment_id`.

## Alternatives Considered

1. Integrate AcquireMock directly inside checkout logic as a special case

   Rejected because it would couple checkout flow to one provider’s redirect/webhook behavior and make future provider replacement more invasive.

2. Treat hosted session creation as successful payment

   Rejected because it can incorrectly mark orders as PAID before the customer completes hosted payment.

3. Use frontend return as proof of payment success

   Rejected because return navigation is UX only; final truth must come from verified backend webhook processing.

4. Keep provider-specific callback URL composition in checkout view

   Rejected because it leaks hosted-provider implementation details into the checkout entrypoint and weakens provider boundary cleanliness.

5. Remove the DEV fake flow once hosted payments exist

   Rejected because the direct dev-compatible flow remains useful for development, test setup, and simplified scenarios.

## Notes

This ADR intentionally does not yet finalize:

- production-grade COD semantics,
- refund / void / chargeback capabilities,
- multi-provider routing policy for the same payment method in production,
- broader provider configuration UI or backoffice tooling,
- whether provider_reference will become mandatory for future providers,
- advanced retry UX beyond the current frontend return/failure flow.

Those remain future evolution topics.
