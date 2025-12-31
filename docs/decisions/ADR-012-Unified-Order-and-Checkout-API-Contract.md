# ADR-012: Unified Order and Checkout API Contract

**Status**: Accepted
**Date**: Sprint 7

## Context

Originally, the Shopwise API exposed **inconsistent response shapes** across endpoints related to orders and checkout:

- `POST /cart/checkout` returned:
  - `order_id`
  - `total`
- Orders endpoints (`GET /orders`, `GET /orders/{id}`) returned:
  - `id`
  - `total_price`
- Order items exposed internal persistence fields such as `price_at_order_time`, whose semantic meaning (unit price vs. line total) was ambiguous.
- Discount information was not explicitly represented in API responses, making it impossible for frontend clients to explain pricing to users.

This inconsistency caused:

- brittle frontend and Postman tests,
- duplicated logic on the client side,
- confusion around pricing semantics,
- increased risk of regressions during refactoring.

The API contract did not clearly separate **domain persistence concerns** from **public API representation**.

## Decision

We unified the public API contract for **checkout and orders** into a single, explicit response shape.

### Unified response contract (order):

```json
{
  "id": <int>,
  "status": <string>,
  "items": [
    {
      "id": <int>,
      "product": <int>,
      "quantity": <int>,
      "unit_price": "100.00",
      "line_total": "80.00",
      "discount": {
        "type": "PERCENT",
        "value": "20.00"
      } | null
    }
  ],
  "total": "80.00"
}
```

**Key changes**:

- `order_id` was replaced by `id` everywhere.
- `total_price` was replaced by `total` everywhere.
- `price_at_order_time` was removed from API responses.
- Order items now explicitly expose:
  - `unit_price`
  - `line_total`
  - `discount` (type + value or null)

Internally, persistence fields (`price_at_order_time`, snapshot columns) are retained but never leaked into the API.

### Principles

- Single source of truth: one response contract for checkout and orders.
- Explicit over implicit: no ambiguous pricing fields.
- Frontend-friendly: no client-side price calculations required.
- Clear separation: database snapshot ≠ API contract.
- Breaking changes are acceptable when correctness and clarity improve.

## Consequences

**Positive**

- Eliminates ambiguity between unit price and line total.
- Simplifies frontend and E2E test logic.
- Enables clear price explanation in UI (discount visibility).
- Makes API documentation (OpenAPI) reflect real behavior.
- Reduces future refactoring risk.

**Negative**

- Breaking change for existing API consumers.
- Required coordinated updates to tests, Postman collections, and documentation.
- Slightly more verbose API responses.
