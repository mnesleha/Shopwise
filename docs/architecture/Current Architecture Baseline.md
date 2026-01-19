# Current Architecture Baseline

**Purpose:** This document describes the **current, authoritative state** of the Shopwise system.
It is a **living document** and should be updated whenever an accepted ADR changes system behavior,
API contracts, data guarantees, or testing strategy.

> ADRs explain **why** decisions were made.  
> This baseline explains **what is true now**.

---

## System Snapshot (Current)

- **Backend:** Django + Django REST Framework
- **API Contract:** OpenAPI is the canonical specification (generated from code and treated as source of truth). (ADR-004)
- **Frontend:** Planned (React + Vite). Language choice (JS vs TS) TBD.
- **Databases:**
  - SQLite for fast unit tests
  - MySQL for production-like behavior (dev/prod and DB-critical integration tests). (ADR-003)
- **Testing Tooling:**
  - Backend: pytest
  - E2E/Contract smoke: Postman collections (until automated contract testing is added)

---

## Architecture Principles (Active)

These principles are currently enforced across the codebase (or within the hardened domains if scope-limited).

### Contract-first API behavior

- OpenAPI is the canonical contract for endpoints, status codes and error payloads. (ADR-004)

### Unified error contract

- All API errors use a consistent payload shape:
  `{ "code": "<string>", "message": "<human readable>" }`
- Domain-specific exceptions are mapped through a single handler. (ADR-009)

### Deterministic pricing

- Orders store pricing snapshots (unit price, discounts, line totals) to guarantee determinism after checkout. (ADR-006)

### Atomic checkout

- Checkout is executed atomically; partial state is not allowed.
- Explicit rollback behavior is applied where needed. (ADR-007)

### Double-checkout protection

- The system prevents converting the same cart multiple times; conflicts return a deterministic error (e.g., 409). (ADR-008)

---

## Domain Boundaries (Current)

This section describes the active bounded contexts / domains and their responsibilities.

- **Cart**: mutable state while ACTIVE; responsible for pricing preview and item management.
- **Order**: immutable snapshot created from a cart during checkout.
- **Payment**: mocked/fake provider integration; separate step from checkout flow.

> Details: see `architecture/Domain Model.md` and `architecture/Cart-Order Lifecycle.md`.

### Product Catalog: Categories

Categories are modeled as a **flat list** with no hierarchy. (ADR-015)

- No `parent` relationship, no `children` nesting, no `is_parent` semantics.
- Categories act as read-only classification labels for products.
- Any grouping or applicability logic for promotions/discounts is handled via explicit targeting (e.g., campaigns selecting specific products), not by traversing a category tree.

Source: [ADR-015](../decisions/ADR-015-Category_Model_Is_Flat.md).

---

## Data & Persistence Guarantees

### Database strategy by environment (Current)

- Unit tests: SQLite (fast feedback loop). (ADR-003)
- Production-like behavior: MySQL (integration confidence). (ADR-003)

### Transactional guarantees (Checkout)

- Checkout changes are atomic.
- Data invariants are protected at the domain/service layer and (where applicable) reinforced by DB constraints/indexes.

---

## API Contract (Current)

### Error model

- Error payload shape is standardized. (ADR-009)
- Error codes are stable identifiers used by clients and tests.

### Contract governance (Current process)

- API changes must update the OpenAPI schema and add/adjust tests.
- Breaking changes require an ADR or explicit decision record.
- Postman CLI tests serve as an executable verification of the OpenAPI contract and expected API behavior. ([ADR-016](../decisions/ADR-016-Postman-CLI-for-API-Contract-and-E2E-Testing-in-CI.md))

### Unified Order + Checkout response shape

Checkout and Orders expose a single, consistent public contract. ([ADR-012](../decisions/ADR-012-Unified-Order-and-Checkout-API-Contract.md))

- `id` is used consistently (no `order_id`)
- `total` is used consistently (no `total_price`)
- Order items expose explicit pricing semantics:
  - `unit_price`
  - `line_total`
  - `discount: { type, value } | null`
- Internal persistence fields (e.g., legacy snapshot columns) are never leaked into the public API.

Source: [ADR-012](../decisions/ADR-012-Unified-Order-and-Checkout-API-Contract.md).

### Categories response shape

Category endpoints return flat category representations only. (ADR-015)

- Nested structures (`children`) and hierarchy-related fields (`parent`, `is_parent`) are not part of the public API contract.
- OpenAPI examples and contract tests must reflect the flat model.

Source: [ADR-015](../decisions/ADR-015-Category_Model_Is_Flat.md).

---

## Pricing Policy (Current)

Pricing is deterministic, audit-friendly, and fully server-calculated. (ADR-013)

Rules:

1. Discounts apply per unit.
2. FIXED wins: if any valid FIXED discount exists, PERCENT discounts are ignored.
3. Discounted unit price is clamped to >= 0.00.
4. Rounding uses ROUND_HALF_UP to 2 decimals:
   - compute discounted unit price → round to 2 decimals
   - line total = rounded_unit_price × quantity → round again to 2 decimals

Checkout snapshots pricing into OrderItem:

- unit_price_at_order_time
- line_total_at_order_time
- applied_discount_type_at_order_time
- applied_discount_value_at_order_time

Legacy field `price_at_order_time` is retained temporarily for backward compatibility and stores the line total, but is not part of the public API.

Source: [ADR-013](../decisions/ADR-013-Pricing-and-Rounding-Policy.md).

---

## Authentication (Current)

The API uses JWT Bearer authentication. (ADR-019)
Clients send `Authorization: Bearer <access_token>`. Roles/permissions are enforced server-side.

JWT-related errors follow the unified error payload conventions.

---

## Identity (Current)

The project uses a custom Django user model (`accounts.User`) with email-based authentication.
Email is required, normalized and unique at the database level. (ADR-020)
All domain relations reference `settings.AUTH_USER_MODEL`.

---

## Anonymous Cart (Current)

Anonymous carts are supported via an opaque guest cart token. (ADR-022)

Token transport:

- Primary: HttpOnly cookie `cart_token`
- Secondary: `X-Cart-Token` header (takes precedence over cookie)

The database stores only a SHA-256 hash of the token (`anonymous_token_hash`).

Cart resolution:

- Authenticated requests resolve the user’s ACTIVE cart (created lazily if missing).
- Anonymous requests resolve an ACTIVE anonymous cart by token hash; if missing/invalid, a new anonymous cart is created and a cookie is set.

Login behavior:

- On successful login, the system adopts or merges the guest cart according to ADR-018.
- After adopt/merge, the token is invalidated and the cookie is cleared.
- Merge conflicts return HTTP 409 `CART_MERGE_STOCK_CONFLICT`.

Cart status model includes terminal `MERGED` for merged anonymous carts.

---

## Active Cart Resolution (Current)

For authenticated users, the system no longer derives the “active cart” by querying `Cart` rows by status.
Instead, it uses a dedicated **ActiveCart pointer** persisted in the database. (ADR-026)

- `ActiveCart` enforces a cross-database invariant: **exactly one active cart reference per user** (unique on `ActiveCart.user`).
- `Cart` rows represent cart history (multiple rows per user may exist over time with lifecycle statuses such as ACTIVE/CONVERTED/MERGED).
- All authenticated cart flows (GET cart, add/update/remove items, merge/adopt on login, checkout conversion) resolve the current cart via `ActiveCartService`.
- Anonymous carts remain token-based and do not use the ActiveCart pointer.

---

## Order Lifecycle (Current)

MVP order status flow: `CREATED -> PAID -> SHIPPED`. (ADR-017)

Inventory is reserved by decrementing `product.stock_quantity` when an order transitions to `PAID`.
This transition and stock decrement are idempotent; repeated payment success processing must not decrement stock twice.
`SHIPPED` is an admin-triggered fulfillment state with no additional pricing or inventory effects.

---

## Guest Checkout and Order Claiming (Current)

The checkout endpoint supports both authenticated and anonymous clients. (ADR-023)

- Anonymous checkout requires customer contact and address snapshot fields (minimum: `customer_email`).
- Orders can be created with `user = NULL` and store customer/contact snapshots for auditability.

### Verified claim policy

Guest orders are only attached to a user account after the user’s email is verified (double opt-in). (ADR-023)

Claim eligibility:

- `order.user IS NULL`
- `order.customer_email` matches the user email (case-insensitive / normalized)
- `user.email_verified == true`

Claim is transactional and idempotent and may run on auth success and/or on email verification.

---

## Cart → Order → Inventory (Current)

The system uses a **two-phase inventory model** that separates stock holding from physical stock decrement.
This design supersedes earlier approaches that decremented stock directly at checkout.

**Key principles**:

- `Cart` represents a mutable shopping intent with **no inventory impact**.
- `Order` is an immutable snapshot created at checkout (`status = CREATED`).
- `Product.stock_quantity` represents **physical stock only**.
- Overselling is prevented via **explicit inventory reservations**.

### Inventory Reservation Model (Current)

At checkout, inventory is **reserved**, not decremented.

- For each order item, an `InventoryReservation` is created with:
  - `status = ACTIVE`
  - explicit `expires_at`` (TTL)
- Availability is computed as:

```python
available = product.stock_quantity
           - sum(quantity of ACTIVE reservations for product)
```

- Physical stock is decremented only after successful payment (`CREATED → PAID`).
- Reservations are terminally resolved as:
  - `COMMITTED` on payment success
  - `RELEASED / EXPIRED` on cancellation or TTL expiry

Reservation TTL is applied at checkout and is environment-configurable
(guest vs authenticated users).

### Order Lifecycle (Current)

Orders follow a minimal, explicit lifecycle:

- `CREATED`
  - inventory reserved
  - awaiting payment
- `PAID`
  - reservations committed
  - physical stock decremented
- `CANCELLED`
  - reservations released or expired
  - physical stock unchanged

Cancellation **reasons are metadata**, not separate states
(e.g. `PAYMENT_FAILED`, `PAYMENT_EXPIRED`, `CUSTOMER_REQUEST`, `OUT_OF_STOCK`).

Planned terminal states:

- `SHIPPED`
- `DELIVERED`

### Time-Based Expiration (TTL)

Inventory reservations are time-bound.

- TTL is evaluated only for:
  - `ACTIVE` reservations
  - orders still in `CREATED`
- Expiration:
  - releases reservations
  - cancels the order with system metadata
- Paid orders are **never expired**.

Expiration is executed by a background runner / management command
(prepared for later scheduling via django-q2).

### Architectural Notes

- Inventory and order state side effects are executed **only via service layer orchestration**.
- Models enforce invariants but contain no side-effect logic.
- The design is **WMS-friendly** and prepared for future external fulfillment integration without refactoring core order models.

### References

- [Cart–Order Lifecycle (current)](./Cart-Order%20Lifecycle.md)
- [Inventory Reservation TTL Lifecycle](./Inventory%20Reservation%20Lifecycle.md)
- [ADR-025: Inventory Reservation Model](../decisions/ADR-025-Inventory-Reservation-Model.md)

---

## Testing Strategy (Current)

### Test pyramid

- **Unit tests (pytest + SQLite):** fast, deterministic, domain/service oriented.
- **DB-behavior integration tests (pytest + MySQL):** required for transactionality and DB-specific behavior.
- **E2E/contract smoke (Postman):** validates workflows from a consumer perspective.

### Critical paths

These flows must remain stable and heavily tested:

- Cart lifecycle: ACTIVE → CONVERTED
- Checkout atomicity + rollback behavior
- Double-checkout conflict handling
- Pricing snapshot invariants
- Unified error payload across hardened domains

### Dual database approach

- SQLite is the default backend for fast unit test feedback.
- A targeted MySQL verification suite validates production-critical DB behavior. (ADR-014)

Markers:

- `@pytest.mark.sqlite` — safe on SQLite (default suite)
- `@pytest.mark.mysql` — must be verified on MySQL

Default run:

- `pytest -m "not mysql"`

MySQL verification run:

- `DJANGO_SETTINGS_MODULE=settings.mysql pytest -m mysql`

MySQL suite is required for changes touching:

- checkout/order/payment flows
- pricing snapshot persistence
- transaction/atomicity boundaries
- constraints/migrations
- DB-originated error mapping and conflict/idempotency behavior

Source: [ADR-014](../decisions/ADR-014-Dual-Database-Testing-Strategy.md).

### MySQL parity note

Historical schema constructs that block MySQL migrations must not remain in the active migration chain.
Where needed, migrations are squashed or rewritten to ensure MySQL parity. ([ADR-015](../decisions/ADR-015-Category_Model_Is_Flat.md), [ADR-014](../decisions/ADR-014-Dual-Database-Testing-Strategy.md))

### API Contract & E2E Verification

End-to-end API behavior is verified in CI using **Postman CLI**, executing cloud-hosted Postman collections against a locally started backend with a real MySQL database. (ADR-016)

Responsibilities:

- CI pipeline prepares the execution environment (DB, migrations, seed data, server startup).
- Postman CLI validates API workflows, authentication, and response behavior.

This layer complements unit and integration tests by validating the system from a consumer perspective.

---

## Migration Policy (Pre-1.0)

Before v1.0, controlled migration resets are allowed for foundational schema changes.
Resets must be documented, reproducible, and validated by CI from a clean state (migrate → seed → tests). (ADR-021)

---

## Known Limitations & Planned Improvements

- Frontend language decision (JS vs TS) pending.
- Full-system rollout of unified error handling and OpenAPI governance pending (currently prioritized domains: carts/checkout).
- Automated OpenAPI contract tests to be introduced (CI enforcement).

---

## Traceability

**Baseline statements are backed by ADRs:**

- [ADR-003 Database Strategy](../decisions/ADR-003-database-strategy.md)
- [ADR-004 OpenAPI as Source of Truth](../decisions/ADR-004-OpenAPI-as-Source-of-Truth.md)
- [ADR-006 Snapshot Pricing Strategy](../decisions/ADR-006-Snapshot-Pricing-Strategy.md)
- [ADR-007 Atomic Checkout with Explicit Rollback](../decisions/ADR-007-Atomic-Checkout-with-Explicit-Rollback.md)
- [ADR-008 Double-checkout Protection](../decisions/ADR-008-Doubleheckout-Protection.md)
- [ADR-009 Unified Error Handling Strategy](../decisions/ADR-009-Unified-Error-Handling-Strategy.md)
