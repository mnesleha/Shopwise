# Architecture & Quality Guard Rules (Sprint Kickoff Checklist)

**Purpose**: Keep Shopwise architecture coherent and prevent sprint-level drift.
**Scope**: Applies to all PRs and refactors unless explicitly overridden by an ADR.

## 1) Contract & Error Semantics (API First, Code Enforced)

- **Unified error payload is mandatory**: `{code, message, errors?}` for all API failures.
- **No `{"detail": ...}` drift** in docs or examples unless explicitly justified.
- API changes must keep **stable error codes** (clients & tests depend on them).
- For “core flow” endpoints, prefer **cart/order snapshots** over partial responses to reduce chatty FE calls.

**Guard check**: If a PR touches serializers/views/exception handling → verify OpenAPI + Postman contract tests remain consistent.

## 2) Authentication & Session Transport

- JWT is stored in **httpOnly cookies**; FE SSR forwards cookies where needed. [(ADR-030)](../decisions/ADR-030-JWT-in-httpOnly-Cookies-with-SSR-Forwarding-Strategy.md)
- **No token leakage** to localStorage/sessionStorage.
- Interceptors must guard against **infinite refresh loops**.
- CORS must explicitly allow:
  - credentials (cookies)
  - `Authorization` header (if used as fallback)
  - custom headers used by carts (e.g., X-Cart-Token)

**Guard check**: Any auth-related PR must include at least one integration test (Postman or FE E2E) proving cookie-based auth works.

## 3) Cart Domain: Active Cart Pointer & Anonymous Token Rules

- Authenticated “current cart” is resolved **only via ActiveCart pointer**. [(ADR-026)](../decisions/ADR-026-ActiveCart-Pointer-Refactor.md)
- Anonymous cart is identified by token (cookie/header precedence) and never uses ActiveCart. [(ADR-022)](../decisions/ADR-022-Anonymous_Cart_Introduction.md)
- **Adopt vs Merge** on login must remain deterministic and idempotent. ([ADR-018](../decisions/ADR-018-Anonymous-Cart-and-Cart-Merge-on-Login.md/), [022](../decisions/ADR-022-Anonymous_Cart_Introduction.md))
- Cart operations must be idempotent where defined (PUT/DELETE semantics).

**Guard check**: No code may “query by status = ACTIVE” to find the current cart for authenticated users.

## 4) Inventory & Fulfillment: Reservation Model Invariants

- `Product.stock_quantity` is **physical stock**.
- Availability is computed as:
  `available = physical_stock - sum(ACTIVE reservations)`
- **Reserve on checkout, commit on payment, release on cancel/expiry**. [(ADR-025)](../decisions/ADR-025-Inventory-Reservation-Model.md)
- Inventory side effects are **service-layer only**:
  - `reserve_for_checkout`
  - `commit_reservations_for_paid`
  - `release_reservations`
  - `expire_overdue_reservations`
- All operations must be **transactional** and **idempotent**.

**Guard check**: Any change in inventory logic requires MySQL verification tests for races/deadlocks.

## 5) Order Lifecycle & State Changes

- Order status changes are guarded (FSM or explicit transition map), but **side effects must remain in service layer**.
- Cancellation requires reason + actor metadata (until full audit coverage exists).
- Admin-only transitions (e.g., ship/deliver) must stay in `/api/v1/admin/...` with RBAC.

**Guard check**: No model `save()` hooks or signals for fulfillment transitions.

## 6) Audit Logging (MVP Discipline)

- Audit events are **append-only** and emitted from service layer. [(ADR-029)](../decisions/ADR-029-Audit-Log-Baseline-Orders.md)
- Audit must be **best-effort** (must not break business flow if audit logging fails).
- Use stable action identifiers (registry pattern), avoid DB enum churn.

**Guard check**: At least these actions should be audited when touched:

- order state changes
- inventory reserve/commit/release/expire
- guest order claim
- admin fulfillment actions

## 7) Testing Strategy (Pyramid + Anti-Flakiness Rules)

- **Unit/domain tests (SQLite)** for logic.
- **MySQL-only tests** for concurrency/locks/constraints.
- **Postman contract tests** validate HTTP status codes and payload shapes.
- **Playwright E2E** validates user-observable behavior, not transport internals.

### Playwright rules [(ADR-031)](../decisions/ADR-031-Playwright-No-waitForResponse-with-Next-Proxy.md)

- Do not use `waitForResponse()` for Next `/api/*` proxy flows.
- Prefer `waitForURL`, stable UI assertions, and `data-testid`.
- Avoid sleeps; prefer `expect.poll()` for eventual consistency.

**Guard check**: Any new E2E flow must be stable across Chromium/Firefox/WebKit.

## 8) Docs & ADR Discipline

- Any cross-cutting change must be captured as:
  - a new ADR, or
  - an explicit update to an existing ADR + baseline patch.
- **Current Architecture Baseline** must reflect the “truth in code” after a change.
- Docs must not assume outdated invariants (e.g., “unique ACTIVE cart row”).

**Guard check**: If a PR changes a core invariant → baseline update is required.

## 9) Non-Blocking SaaS/White-Label Guardrails

- Keep shop identity & external links configurable (e.g., `PUBLIC_BASE_URL`). ([ADR-027](../decisions/ADR-027-PUBLIC_BASE_URL-for-externally-shared-links.md))
- Separate public vs admin surface areas.
- Infrastructure artifacts (audit events, cleanup jobs) should be **scope-aware** (nullable context) without implementing multi-tenancy yet.

**Guard check**: Avoid hardcoding shop identity/branding in business logic.

## 10) “Stop the Line” Triggers (Escalate to ADR/Review)

If any of these occur, pause implementation and decide explicitly:

- inconsistent meaning of `stock_quantity`
- new cart resolution logic bypassing ActiveCart
- auth cookie/SameSite/CSRF changes
- introducing non-idempotent side effects in checkout/payment flows
- flaky E2E that requires sleeps/timeouts to pass
- OpenAPI drift vs runtime behavior

## Sprint Kickoff Routine (Recommended)

- Pick the sprint’s “core flow” and list its endpoints.
- Confirm error codes & snapshots for that flow.
- Confirm which tests will be the gates (unit/MySQL/Postman/Playwright).
- Identify any new invariants → ADR before implementation.
