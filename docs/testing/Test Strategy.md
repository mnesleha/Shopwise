# Test Strategy

## Purpose

This document describes the current testing strategy of the Shopwise project.

It explains:

- what kinds of tests exist
- what each layer is responsible for
- how test responsibilities are intentionally separated
- how testing supports architecture governance and safe evolution

Shopwise is a QA/SDET-oriented showcase project.
Testing is therefore not treated as an auxiliary activity, but as a **core architectural mechanism**.

---

## 1. Testing Philosophy

Shopwise uses a **layered testing strategy** designed to balance:

- speed of feedback
- architectural confidence
- runtime realism
- maintainability
- resistance to flaky behavior

Testing is intentionally aligned with the project architecture:

- domain logic is tested close to the backend service layer
- transport contracts are tested at API level
- browser behavior is tested at E2E level
- concurrency-sensitive behavior is verified against MySQL
- performance is measured separately from correctness

The goal is not “maximum number of tests”, but **clear responsibility per layer**.

---

## 2. Core Principles

### 2.1 Backend is the source of business truth

Tests must reinforce the rule that authoritative business outcomes are computed by backend services.

Frontend tests may verify presentation and user flow, but they must not become the primary proof of pricing, tax, payment, inventory, or shipping correctness.

### 2.2 Each layer has a distinct job

Different test layers answer different questions:

- **unit/domain tests** → is the business logic correct?
- **MySQL verification tests** → does it remain correct under real DB behavior and concurrency?
- **API/contract tests** → does the HTTP contract behave as documented?
- **frontend tests** → does the UI render and react correctly?
- **browser E2E tests** → can a user actually complete important flows?
- **performance tests** → how does the system behave under representative load?

A layer should not duplicate another layer unless the duplication is intentional and justified.

### 2.3 Flaky tests are treated as architecture problems

If a test is unstable, the preferred response is not to increase sleeps/timeouts, but to:

- identify the real runtime or synchronization problem
- move the assertion to the correct test layer
- improve system observability or determinism
- update architectural guard rules if needed

### 2.4 Testability is part of design

Design decisions are expected to support testability:

- side effects belong in service layer orchestration
- provider integrations are abstracted
- order history is snapshot-based
- cart and auth resolution rules are explicit
- pricing pipelines are centralized
- runtime truth is not split across frontend and backend

---

## 3. Test Layers

## 3.1 Backend Unit and Domain Tests

**Primary tool:** `pytest`

These tests validate core domain logic close to the implementation of business rules.

Typical scope:

- service-layer behavior
- model invariants
- validation rules
- pricing rules
- inventory reservation rules
- order lifecycle rules
- guest checkout / guest claim rules
- payment and shipping application logic (without real provider transport)

Characteristics:

- fast
- deterministic
- narrow in scope
- focused on business correctness

These tests should be the first line of defense for logic regressions.

---

## 3.2 MySQL Verification Tests

**Primary tool:** `pytest` with MySQL-specific configuration and markers

These tests exist because SQLite is intentionally used for fast local feedback, but it does not reproduce all relevant production-like database behavior.

MySQL verification tests are required for:

- race conditions
- row locking behavior
- `select_for_update()` semantics
- deadlock-sensitive flows
- uniqueness constraints under contention
- idempotence under duplicate provider callbacks
- cart pointer / active cart concurrency
- payment / inventory / reservation conflict scenarios

Typical examples:

- two concurrent reservations on last available stock
- concurrent cart creation / active cart resolution
- duplicate webhook delivery with idempotent result application
- commit vs release / expiration races

These tests are slower and more specialized than standard unit tests, but they are essential for architectural correctness.

---

## 3.3 API Contract and Workflow Tests

**Primary tool:** Postman

Postman is used to validate:

- request/response contracts
- status codes
- error payloads
- authentication flows
- guest flows
- API-level business workflows

This layer answers:

> “Does the backend behave correctly as an HTTP API?”

Postman tests are especially important for:

- auth flows
- guest checkout flows
- claim flows
- order and payment workflows
- provider callback scenarios
- structured error contract verification

Postman is also used in CI and is part of the project’s contract validation strategy.

### Important boundary

Postman is not used to prove low-level business correctness that is already covered by backend tests.
Its role is API-level contract and workflow validation.

---

## 3.4 Frontend Unit / Integration Tests

**Primary tool:** Vitest/React Testing Library

Vitest is used to validate frontend-local behavior such as:

- rendering logic
- component state transitions
- helper utilities
- frontend-specific composition logic
- interaction with mocked API/client layers

These tests answer:

> “Does the frontend code behave correctly in isolation?”

They are not intended to prove backend business truth.

---

## 3.5 Browser End-to-End Tests

**Primary tool:** Playwright

Playwright tests validate **real user-observable behavior** across the browser and full frontend/backend integration.

Typical flows:

- authentication
- guest cart and checkout
- order visibility
- email-driven account/order flows
- cart badge updates
- SSR/CSR boundary behavior

This layer answers:

> “Can the user actually complete the flow in a real browser?”

### E2E philosophy

Playwright verifies:

- navigation
- rendered UI state
- user-visible messages
- browser-level interaction correctness

Playwright does **not** serve as the primary source of truth for:

- backend status codes
- detailed API transport assertions
- provider callback contract semantics already covered by backend/API test layers

---

## 3.6 Performance Baseline Tests

**Primary tool:** Locust

Locust is used to establish performance baselines and representative traffic patterns.

This layer answers:

> “How does the system behave under synthetic load?”

Its role is not functional correctness but performance visibility.

Typical uses:

- catalogue browsing baseline
- cart flow baseline
- authenticated vs unauthenticated request behavior
- performance before/after major architecture changes

Performance tests should be interpreted together with architecture changes, database behavior, and deployment model.

---

## 4. Layer Responsibilities Summary

| Layer                     | Main purpose                            | Primary tools  |
| ------------------------- | --------------------------------------- | -------------- |
| Backend unit/domain       | Business rule correctness               | pytest         |
| MySQL verification        | Concurrency and DB-specific correctness | pytest + MySQL |
| API contract/workflow     | HTTP contract and workflow validation   | Postman        |
| Frontend unit/integration | Frontend-local correctness              | Vitest/RTL     |
| Browser E2E               | User-observable flow validation         | Playwright     |
| Performance baseline      | Load and runtime behavior               | Locust         |

---

## 5. Special Testing Rules

## 5.1 MySQL is authoritative for concurrency-sensitive flows

SQLite is acceptable for fast feedback, but not for proving concurrency or locking correctness.

If a change affects:

- inventory reservations
- payment callback idempotence
- active cart resolution
- provider webhook processing
- shipping event application
- unique constraints under contention

then MySQL verification tests are required.

---

## 5.2 Playwright must avoid transport-coupled flakiness

For frontend flows going through Next.js proxy/rewrite behavior:

- Playwright must not use `waitForResponse()` as the main assertion mechanism
- prefer `waitForURL`, visible UI state, and stable `data-testid` selectors
- avoid arbitrary sleeps
- prefer deterministic UI synchronization patterns

### SSR / hydration guard

For simple SSR-rendered forms:

- prefer uncontrolled inputs
- avoid unnecessary controlled-input hydration races

---

## 5.3 Frontend must not become a shadow pricing engine

Frontend tests must never “reconstruct” authoritative prices, tax, or discount logic independently of backend output.

Frontend may verify:

- correct display of backend-provided values
- messaging
- UX behavior
- route transitions

but not become a parallel business rules engine.

---

## 5.4 Provider mocks must remain integration boundaries

Payment and shipping provider mocks are treated as integration boundaries, not as internal implementation shortcuts.

Their behavior should be tested through:

- backend services
- provider callback handling
- E2E user flows where relevant

but domain truth must still be asserted in backend tests.

---

## 6. Testing by Domain

## Identity and Authentication

Covered by:

- pytest
- Postman
- Playwright

Includes:

- register / login / refresh / logout
- `/auth/me`
- cookie-based JWT transport
- SSR/session continuity
- account security operations
- throttling of abuse-prone flows

## Cart and Checkout

Covered by:

- pytest
- MySQL verification
- Postman
- Playwright

Includes:

- anonymous cart
- ActiveCart pointer behavior
- merge/adopt
- guest checkout
- order creation
- checkout contract

## Inventory and Orders

Covered by:

- pytest
- MySQL verification
- Postman

Includes:

- reservation lifecycle
- cancellation / expiration
- order snapshots
- inventory commit/release rules
- idempotent state application

## Payments

Covered by:

- pytest
- MySQL verification where needed
- Postman
- Playwright (return flow UX)

Includes:

- provider-agnostic payment behavior
- hosted initiation
- webhook/callback application
- idempotence and duplicate handling
- separation of frontend return UX from payment truth

## Shipping

Covered by:

- pytest
- Postman
- optional browser validation for exposed customer UI

Includes:

- shipment creation after paid state
- provider-agnostic shipping behavior
- status projection to order/customer views
- idempotent shipping event application

## Catalogue / Search / Media

Covered by:

- pytest
- Postman
- frontend tests
- browser checks where useful

Includes:

- category model assumptions
- search behavior
- media URL usage
- product listing and detail rendering

---

## 7. CI and Test Execution Model

Tests are executed through GitHub Actions workflows and local development flows.

The exact workflow split is described in CI/CD documentation, but conceptually:

- backend validation runs automatically
- frontend/browser validation runs automatically
- documentation deployment is automated
- test layers are intentionally separated rather than collapsed into one giant pipeline

This separation makes failures easier to diagnose and keeps each layer accountable for its own scope.

---

## 8. Quality Gates (Conceptual)

A change is not considered safe merely because “some tests passed”.

The intended quality gate mindset is:

- backend/domain logic must be validated where it belongs
- DB-sensitive logic must be proven against MySQL
- API behavior must be validated as API behavior
- user-visible flows must be validated in the browser
- significant architecture changes should update docs and ADRs when needed

Testing is therefore one part of a larger quality system that also includes:

- architecture guard rules
- ADR discipline
- baseline maintenance
- documentation review

---

## 9. Anti-Patterns to Avoid

The following are considered unhealthy testing patterns in this project:

- using Playwright to validate low-level API transport details already covered elsewhere
- solving browser flakiness with arbitrary sleeps
- asserting backend business rules only through frontend tests
- skipping MySQL verification for concurrency-sensitive changes
- duplicating pricing/tax logic in frontend tests
- treating mock providers as proof of domain correctness without backend assertions
- letting documentation drift from actual tested behavior

---

## 10. Current Strengths

The current testing architecture is especially strong in these areas:

- domain/service-layer validation
- MySQL-backed concurrency verification
- API contract coverage
- browser-based validation of critical flows
- architecture-aware testing decisions captured via ADRs

---

## 11. Known Gaps / Active Evolution Areas

The testing strategy continues to evolve together with the system.

Active areas of ongoing refinement include:

- pricing / VAT / promotions coverage strategy
- broader shipping and payment provider scenarios
- performance baselines for realistic frontend-driven traffic
- test documentation cleanup and consolidation
- future tightening of CI quality gates as the system stabilizes

---

## 12. Related Documents

### Core references

- [Current Architecture Baseline](../architecture/Current%20Architecture%20Baseline.md)
- [Architecture & Quality Guard Rules](../architecture/Architecture%20%26%20Quality%20Guard%20Rules.md)
- [ADR Index](../decisions/readme.md)

### Domain flow documents

- [Cart–Order Lifecycle](../architecture/Cart-Order%20Lifecycle.md)
- [Inventory Reservation Lifecycle](../architecture/Inventory%20Reservation%20Lifecycle.md)

### Integration / CI

- [Postman CLI in CI](../architecture/Postman%20CLI%20in%20CI.md)
- [Postman Anonymous Cart Testing](../architecture/Postman%20Anonymous%20Cart%20Testing.md)
- [Pipeline Overview](../ci-cd/Pipeline%20Overview.md)
- [Quality Gates](../ci-cd/Quality%20Gates.md)
