# Quality Discovery – OpenAPI Integration

## Purpose

This document captures quality-related findings discovered
during OpenAPI documentation of the backend API.

The goal is to identify:

- ambiguous behavior
- missing validations
- undocumented business rules
- misalignment between implementation and intended API contract

## Cart Domain – Findings

### POST /cart/items/

#### 1. Missing error handling for non-existing product

- Endpoint: POST /cart/items/
- Current behavior: unhandled exception (500)
- Expected behavior: 404 Not Found
- Impact: frontend integration, unclear API contract

Status: Identified

Proposed action: Add explicit product existence validation

JIRA: SHOP-111

#### 2. Undefined business conflict scenarios

- Scenario: product exists but is unavailable
- Expected behavior: 409 Conflict
- Current behavior: not implemented
- Impact: race conditions under load

Status: Identified

JIRA: SHOP-114

#### 3. Implicit cart lifecycle rules

- Rule: user can have only one ACTIVE cart
- Rule: checkout converts cart to CONVERTED
- Current state: enforced in code, not documented
- Impact: unclear expected behavior

Status: Documented via OpenAPI

### POST /cart/checkout/

#### 1. No double checkout protection

- race condition risk
- suitable for 409

JIRA: SHOP-123

#### 2. Error 404 vs 400 not aligned with implementation

- today returns 400
- contract says 404

JIRA: SHOP-124

#### 3. Unresolved rollback on error

- what if OrderItem fails?
- cart can already be CONVERTED

### GET /cart/

#### 1. GET endpoint has side-effect

- is not purely read-only
- must be explicitly described

STATUS: Properly documented via OpenAPI

#### 2. HTTP status code does not match domain reality

- always 200
- even on create

#### 3. Idempotence is not obvious

Repeated call:

- does not change state (mostly)
- but first call may create resource

STATUS: Properly documented via OpenAPI

### GET /orders/

- Orders are immutable, read-only resources.
- Orders are created exclusively via cart checkout.
- No explicit order state transition rules are documented yet.
- Order status lifecycle exists but is not formalized.
- Access control is correctly enforced at query level.

### POST /payments/

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
