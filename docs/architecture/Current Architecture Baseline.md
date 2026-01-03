# Current Architecture Baseline

**Purpose:** This document describes the **current, authoritative state** of the Shopwise system.
It is a **living document** and should be updated whenever an accepted ADR changes system behavior,
API contracts, data guarantees, or testing strategy.

> ADRs explain **why** decisions were made.  
> This baseline explains **what is true now**.

---

## 1 System Snapshot (Current)

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

## 2 Architecture Principles (Active)

These principles are currently enforced across the codebase (or within the hardened domains if scope-limited).

### 2.1 Contract-first API behavior

- OpenAPI is the canonical contract for endpoints, status codes and error payloads. (ADR-004)

### 2.2 Unified error contract

- All API errors use a consistent payload shape:
  `{ "code": "<string>", "message": "<human readable>" }`
- Domain-specific exceptions are mapped through a single handler. (ADR-009)

### 2.3 Deterministic pricing

- Orders store pricing snapshots (unit price, discounts, line totals) to guarantee determinism after checkout. (ADR-006)

### 2.4 Atomic checkout

- Checkout is executed atomically; partial state is not allowed.
- Explicit rollback behavior is applied where needed. (ADR-007)

### 2.5 Double-checkout protection

- The system prevents converting the same cart multiple times; conflicts return a deterministic error (e.g., 409). (ADR-008)

---

## 3 Domain Boundaries (Current)

This section describes the active bounded contexts / domains and their responsibilities.

- **Cart**: mutable state while ACTIVE; responsible for pricing preview and item management.
- **Order**: immutable snapshot created from a cart during checkout.
- **Payment**: mocked/fake provider integration; separate step from checkout flow.

> Details: see `architecture/Domain Model.md` and `architecture/Cart-Order Lifecycle.md`.

### 3.1 Product Catalog: Categories

Categories are modeled as a **flat list** with no hierarchy. (ADR-015)

- No `parent` relationship, no `children` nesting, no `is_parent` semantics.
- Categories act as read-only classification labels for products.
- Any grouping or applicability logic for promotions/discounts is handled via explicit targeting (e.g., campaigns selecting specific products), not by traversing a category tree.

Source: [ADR-015](../decisions/ADR-015-Category_Model_Is_Flat.md).

---

## 4 Data & Persistence Guarantees

### 4.1 Database strategy by environment (Current)

- Unit tests: SQLite (fast feedback loop). (ADR-003)
- Production-like behavior: MySQL (integration confidence). (ADR-003)

### 4.2 Transactional guarantees (Checkout)

- Checkout changes are atomic.
- Data invariants are protected at the domain/service layer and (where applicable) reinforced by DB constraints/indexes.

---

## 5 API Contract (Current)

### 5.1 Error model

- Error payload shape is standardized. (ADR-009)
- Error codes are stable identifiers used by clients and tests.

### 5.2 Contract governance (Current process)

- API changes must update the OpenAPI schema and add/adjust tests.
- Breaking changes require an ADR or explicit decision record.
- Postman CLI tests serve as an executable verification of the OpenAPI contract and expected API behavior. ([ADR-016](../decisions/ADR-016-Postman-CLI-for-API-Contract-and-E2E-Testing-in-CI.md))

### 5.3 Unified Order + Checkout response shape

Checkout and Orders expose a single, consistent public contract. ([ADR-012](../decisions/ADR-012-Unified-Order-and-Checkout-API-Contract.md))

- `id` is used consistently (no `order_id`)
- `total` is used consistently (no `total_price`)
- Order items expose explicit pricing semantics:
  - `unit_price`
  - `line_total`
  - `discount: { type, value } | null`
- Internal persistence fields (e.g., legacy snapshot columns) are never leaked into the public API.

Source: [ADR-012](../decisions/ADR-012-Unified-Order-and-Checkout-API-Contract.md).

### 5.4 Categories response shape

Category endpoints return flat category representations only. (ADR-015)

- Nested structures (`children`) and hierarchy-related fields (`parent`, `is_parent`) are not part of the public API contract.
- OpenAPI examples and contract tests must reflect the flat model.

Source: [ADR-015](../decisions/ADR-015-Category_Model_Is_Flat.md).

---

## 6 Pricing Policy (Current)

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

## 7 Testing Strategy (Current)

### 7.1 Test pyramid

- **Unit tests (pytest + SQLite):** fast, deterministic, domain/service oriented.
- **DB-behavior integration tests (pytest + MySQL):** required for transactionality and DB-specific behavior.
- **E2E/contract smoke (Postman):** validates workflows from a consumer perspective.

### 7.2 Critical paths

These flows must remain stable and heavily tested:

- Cart lifecycle: ACTIVE → CONVERTED
- Checkout atomicity + rollback behavior
- Double-checkout conflict handling
- Pricing snapshot invariants
- Unified error payload across hardened domains

### 7.3 Dual database approach

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

### 7.4 MySQL parity note

Historical schema constructs that block MySQL migrations must not remain in the active migration chain.
Where needed, migrations are squashed or rewritten to ensure MySQL parity. ([ADR-015](../decisions/ADR-015-Category_Model_Is_Flat.md), [ADR-014](../decisions/ADR-014-Dual-Database-Testing-Strategy.md))

### 7.5 API Contract & E2E Verification

End-to-end API behavior is verified in CI using **Postman CLI**, executing cloud-hosted Postman collections against a locally started backend with a real MySQL database. (ADR-016)

Responsibilities:

- CI pipeline prepares the execution environment (DB, migrations, seed data, server startup).
- Postman CLI validates API workflows, authentication, and response behavior.

This layer complements unit and integration tests by validating the system from a consumer perspective.

---

## 8 Known Limitations & Planned Improvements

- Frontend language decision (JS vs TS) pending.
- Full-system rollout of unified error handling and OpenAPI governance pending (currently prioritized domains: carts/checkout).
- Automated OpenAPI contract tests to be introduced (CI enforcement).

---

## 9 Traceability

**Baseline statements are backed by ADRs:**

- [ADR-003 Database Strategy](../decisions/ADR-003-database-strategy.md)
- [ADR-004 OpenAPI as Source of Truth](../decisions/ADR-004-OpenAPI-as-Source-of-Truth.md)
- [ADR-006 Snapshot Pricing Strategy](../decisions/ADR-006-Snapshot-Pricing-Strategy.md)
- [ADR-007 Atomic Checkout with Explicit Rollback](../decisions/ADR-007-Atomic-Checkout-with-Explicit-Rollback.md)
- [ADR-008 Double-checkout Protection](../decisions/ADR-008-Doubleheckout-Protection.md)
- [ADR-009 Unified Error Handling Strategy](../decisions/ADR-009-Unified-Error-Handling-Strategy.md)
