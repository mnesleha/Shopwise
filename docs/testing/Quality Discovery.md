# Quality Discovery – OpenAPI Integration

## Purpose

This document captures quality-related findings discovered
during OpenAPI documentation of the backend API.

The goal is to identify:

- ambiguous behavior
- missing validations
- undocumented business rules
- misalignment between implementation and intended API contract

## Initial Findings

### Cart Domain

#### POST /cart/items/

##### 1. Missing error handling for non-existing product

- Endpoint: POST /cart/items/
- Current behavior: unhandled exception (500)
- Expected behavior: 404 Not Found
- Impact: frontend integration, unclear API contract

Status: Identified

Proposed action: Add explicit product existence validation

JIRA: SHOP-111

##### 2. Undefined business conflict scenarios

- Scenario: product exists but is unavailable
- Expected behavior: 409 Conflict
- Current behavior: not implemented
- Impact: race conditions under load

Status: Identified

JIRA: SHOP-114

##### 3. Implicit cart lifecycle rules

- Rule: user can have only one ACTIVE cart
- Rule: checkout converts cart to CONVERTED
- Current state: enforced in code, not documented
- Impact: unclear expected behavior

Status: Documented via OpenAPI

#### POST /cart/checkout/

##### 1. No double checkout protection

- race condition risk
- suitable for 409

JIRA: SHOP-123

##### 2. Error 404 vs 400 not aligned with implementation

- today returns 400
- contract says 404

JIRA: SHOP-124

##### 3. Unresolved rollback on error

- what if OrderItem fails?
- cart can already be CONVERTED

#### GET /cart/

##### 1. GET endpoint has side-effect

- is not purely read-only
- must be explicitly described

STATUS: Properly documented via OpenAPI

##### 2. HTTP status code does not match domain reality

- always 200
- even on create

##### 3. Idempotence is not obvious

Repeated call:

- does not change state (mostly)
- but first call may create resource

STATUS: Properly documented via OpenAPI

### Orders Domain

#### GET /orders/

- Orders are immutable, read-only resources.
- Orders are created exclusively via cart checkout.
- No explicit order state transition rules are documented yet.
- Order status lifecycle exists but is not formalized.
- Access control is correctly enforced at query level.

### Payments Domain

#### POST /payments/

- Payments are synchronous and simulated (fake gateway).
- Payment creation has immediate side effects on order status.
- No idempotency or retry mechanism is implemented.
- Only one payment per order is allowed.
- Payment lifecycle is minimal and not extensible.

### Products Domain

- Products are exposed as read-only resources.
- Only active and in-stock products are visible via API.
- Product availability filtering is enforced at query level.
- Stock quantity is informational and does not imply reservation.

### Categories Domain

- Categories are hierarchical with a fixed two-level structure.
- Only parent categories are exposed as top-level resources.
- Child categories are embedded and read-only.
- Category tree depth is enforced by model validation.

### Discounts Domain

- Discounts are exposed as read-only resources.
- Only active discounts within validity period are returned.
- Discounts target either a product or a leaf category.
- Category-targeted discounts are not explicitly represented in API payload.
- Discount application logic is intentionally out of API scope.

## OpenAPI Implementation Summary

OpenAPI was used not only as documentation, but also as:

- quality inspection tool
- technical debt detection tool
- design validation tool

Areas identified:

- missing / implicit error scenarios (400 / 404 / 409)
- inconsistencies between business decisions and the model
- implicit state transitions
- missing explicit contracts

**Findings were documented and transferred to the backlog**

## Impact of OpenAPI Adoption

### Contract Changes Identified and Introduced

#### GET /cart

- Explicitly documented dual behavior:
  - 200 OK when an active cart already exists
  - 201 Created when a new active cart is created
- Clarified authentication behavior (401 Unauthorized vs implicit 403 behavior before)

#### POST /cart/items

- Introduced explicit error contracts:
  - 404 Not Found – product does not exist
  - 409 Conflict – product exists but is unavailable (inactive or out of stock)
  - 400 Bad Request – invalid input (e.g. quantity ≤ 0)
- Aligned API behavior with documented OpenAPI responses

#### POST /cart/checkout

- Standardized response contract:
  - Checkout returns an explicit order object instead of implicit root-level fields
- Clarified error scenarios:
  - No active cart
  - Empty cart
  - Repeated checkout attempt (treated as business invalid state, not technical error)
- Explicitly documented error response structure

#### Payments

- Checkout response change (order.id nesting) propagated to payment creation flow
- Payment endpoints now rely on a clearly defined order contract

### Refactoring Triggered by OpenAPI Findings

- Introduced explicit response serializers (e.g. Checkout response) instead of ad-hoc dictionaries
- Unified and centralized error response structure across Cart, Checkout and Payments
- Fixed multiple implicit assumptions uncovered by OpenAPI:
  - Serializer fields returning inconsistent shapes
  - Incorrect HTTP status codes (e.g. 400 vs 409)
  - Missing edge-case handling leading to 500 errors
- Refactored cart and checkout logic to better separate:
  - Validation
  - Business rules
  - Response serialization
- Aligned pytest and Postman tests with the same API contract, eliminating hidden divergences

### Business Value Achieved

- API behavior is now predictable and explicit, reducing ambiguity for frontend integration
- Business error states (out-of-stock, invalid checkout, inactive products) are now first-class citizens, not runtime accidents
- Checkout flow is clearly defined and resilient against invalid states
- The API now represents a realistic e-commerce backend, not a happy-path prototype

### Technical Value Achieved

- OpenAPI became a source of truth, not a passive documentation artifact
- Significant reduction of:
  - Implicit behavior
  - Undocumented assumptions
  - Accidental 500 errors
- Tests (Postman + pytest) now:
  - Validate behavior, not implementation
  - Enforce contract stability during refactoring
- Improved readiness for:
  - CI/CD automation
  - Contract testing
  - Future domain iterations without fear of regression

### Key Takeaway

OpenAPI did not just document the system —
it **exposed structural weaknesses, forced hard decisions**, and **drove meaningful refactoring** that improved both business correctness and technical quality.
