# Architecture & Process Decision Records (ADR Index)

This directory contains the project’s **Architecture Decision Records (ADRs)**.

ADRs document important architectural and process decisions with long-term impact on the system, development workflow, or runtime model.

For the **current effective system state**, see:

- [Current Architecture Baseline](../architecture/Current%20Architecture%20Baseline.md)

---

## How to Use ADRs

- Read the **Current Architecture Baseline** first if you want to understand the system as it works today.
- Read ADRs when you want to understand:
  - why something was designed this way,
  - why a refactor happened,
  - or why a constraint/guardrail exists.

ADRs are historical decision records.  
They are **not** the primary source of current runtime truth.

---

## Decision Types

ADRs in this project document two kinds of decisions:

- **Architecture** — system design, domain boundaries, API behavior, infrastructure/runtime constraints
- **Process** — delivery model, CI/testing workflow, quality governance

Decision type is declared explicitly in each ADR header.

---

## ADR Index

## Core Architecture Foundations

### [ADR-001 – Initial System Architecture](./ADR-001-Project-Setup-Decisions.md)

Defines the initial project setup and foundational architecture direction.

### [ADR-003 – Database Strategy (SQLite vs MySQL)](./ADR-003-Database-Strategy-SQLite-vs-MySQL.md)

Defines SQLite for fast unit tests and MySQL for production-like behavior and DB-critical verification.

### [ADR-004 – OpenAPI as Source of Truth](./ADR-004-OpenAPI-as-Source-of-Truth.md)

Establishes OpenAPI as the authoritative API contract for status codes, payload shapes, and expected behavior.

### [ADR-006 – Snapshot Pricing Strategy](./ADR-006-Snapshot-Pricing-Strategy.md)

Introduces historical price snapshotting at checkout to preserve order-time truth.

### [ADR-007 – Atomic Checkout with Explicit Rollback](./ADR-007-Atomic-Checkout-with-Explicit-Rollback.md)

Defines checkout as an atomic operation and prevents partial conversion side effects.

### [ADR-008 – Double-Checkout Protection](./ADR-008-Double-Checkout-Protection.md)

Prevents converting the same cart multiple times and defines deterministic conflict handling.

### [ADR-009 – Unified Error Handling Strategy](./ADR-009-Unified-Error-Handling-Strategy.md)

Introduces a unified API error contract and centralized exception handling.

---

## Orders, Pricing, Inventory, Fulfillment

### [ADR-012 – Unified Order and Checkout API Contract](./ADR-012-Unified-Order-and-Checkout-API-Contract.md)

Unifies public order and checkout response shapes and removes persistence-specific leakage from the contract.

### [ADR-013 – Pricing and Rounding Policy](./ADR-013-Pricing-and-Rounding-Policy.md)

Defines deterministic rounding behavior and discount precedence rules for the pre-VAT pricing model.

### [ADR-017 – Inventory Reservation and Order Status Policy](./ADR-017-Inventory-Reservation-and-Order-Status-Policy.md)

Introduces the order-state direction for paid/fulfilled flow and inventory-related orchestration.

### [ADR-025 – Inventory Reservation Model](./ADR-025-Inventory-Reservation-Model.md)

Defines reserve-on-checkout, commit-on-payment, release-on-cancel/expiry, and physical stock semantics.

### [ADR-029 – Audit Log Baseline (Orders)](./ADR-029-Audit-Log-Baseline-Orders.md)

Introduces a dedicated audit log MVP for order/inventory-related domain events.

### [ADR-039 – Pricing Foundation and Tax Policy](./ADR-039-Pricing-Foundation-and-Tax-Policy.md)

Introduces canonical NET pricing, tax layering, and backend pricing authority.

### [ADR-040 – Promotion Model and Snapshot Pricing Evolution](./ADR-040-Promotion-Model-and-Snapshot-Pricing-Evolution.md)

Establishes promotions as first-class pricing objects and separates definition, targeting, resolution, and snapshots.

### [ADR-041 – Pricing Calculation Pipeline and Rounding Policy](./ADR-041-Pricing-Calculation-Pipeline-and-Rounding-Policy.md)

Defines the canonical pricing pipeline across NET prices, promotions, tax calculation, and rounded totals.

### [ADR-042 – Promotion Resolution and Controlled Stacking Policy](./ADR-042-Promotion-Resolution-and-Controlled-Stacking-Policy.md)

Defines controlled stacking across promotion layers with deterministic resolution.

### [ADR-043 – Order Line Pricing Snapshot Schema](./ADR-043-Order-Line-Pricing-Snapshot-Schema.md)

Defines explicit line-level order pricing snapshots for historical pricing truth.

### [ADR-044 – Order-Level Discounts and Acquisition Strategy](./ADR-044-Order-Level-Discounts-and-Acquisition-Strategy.md)

Defines order-level discounts as a distinct pricing layer and frames discount acquisition as part of commercial UX.

---

## Identity, Auth, Cart, Checkout

### [ADR-018 – Anonymous Cart and Cart Merge on Login](./ADR-018-Anonymous-Cart-and-Cart-Merge-on-Login.md)

Defines guest cart adoption/merge behavior and deterministic merge rules.

### [ADR-019 – Authentication Strategy (Session-Based vs JWT)](./ADR-019-Authentication-Strategy-Session-Based-vs-JWT.md)

Selects JWT-based authentication as the API auth direction.

### [ADR-020 – Custom User Model with Email-Based Authentication](./ADR-020-Custom-User-Model-with-Email-Based-Authentication.md)

Introduces a custom user model with email as the primary identifier.

### [ADR-022 – Anonymous Cart Introduction](./ADR-022-Anonymous_Cart_Introduction.md)

Defines token-based anonymous carts, resolution strategy, and merge/adopt mechanics.

### [ADR-023 – Guest Checkout and Verified Claim of Guest Orders](./ADR-023-Guest-Checkout-and-Verified-Claim-of-Guest-Orders.md)

Defines guest checkout and safe post-verification claiming of guest orders.

### [ADR-026 – ActiveCart Pointer Refactor](./ADR-026-ActiveCart-Pointer-Refactor.md)

Introduces a dedicated ActiveCart pointer for authenticated users and removes status-based cart resolution assumptions.

### [ADR-030 – JWT in httpOnly Cookies with SSR Forwarding Strategy](./ADR-030-JWT-in-httpOnly-Cookies-with-SSR-Forwarding-Strategy.md)

Defines the current auth transport model for Next.js SSR-compatible frontend integration.

### [ADR-033 – Cart Merge Must Not Block Authentication](./ADR-033-Cart-Merge-Must-Not-Block-Authentication.md)

Separates authentication success from best-effort cart merge outcomes.

### [ADR-035 – Account Email Change Flow](./ADR-035-Account-Email-Change-Flow.md)

Defines secure pending-request-based email change with confirmation and logout-all behavior.

### [ADR-036 – API Throttling Strategy](./ADR-036-API-Throttling-Strategy.md)

Defines throttling rules for abuse-prone auth/account flows.

---

## Catalogue, Media, Search

### [ADR-015 – Category Model Is Flat](./ADR-015-Category_Model_Is_Flat.md)

Defines categories as a flat model without hierarchy.

### [ADR-037 – Product Media Storage Strategy](./ADR-037-Product-Media-Storage-Strategy.md)

Defines media storage abstraction and separation of structured catalogue media vs editorial content uploads.

### [ADR-038 – MySQL `ngram` Parser for MMP Catalogue Search](./ADR-038-MySQL-ngram-parser-for-MMP-catalogue-search.md)

Approves a MySQL-specific search backend implementation while keeping API/service boundaries database-agnostic.

---

## Payments, Shipping, External Providers

### [ADR-045 – Provider-Agnostic Payment Architecture](./ADR-045-Provider-Agnostic-Payment-Architecture.md)

Establishes the provider abstraction model for payments.

### [ADR-046 – Provider-Agnostic Payments Architecture](./ADR-046-Provider-Agnostic-Payments-Architecture.md)

Finalizes the implemented payment architecture with AcquireMock as the first hosted provider.

### [ADR-047 – Carrier-Agnostic Shipping Architecture](./ADR-047-Carrier-Agnostic-Shipping-Architecture.md)

Defines pluggable shipment provider architecture with a mock carrier as the first implementation.

---

## Frontend, SSR, E2E Reliability

### [ADR-027 – `PUBLIC_BASE_URL` for Externally Shared Links](./ADR-027-PUBLIC_BASE_URL-for-externally-shared-links.md)

Defines a single configuration source for public-facing links used in emails and externally shared flows.

### [ADR-031 – Playwright: No `waitForResponse()` with Next Proxy](./ADR-031-Playwright-No-waitForResponse-with-Next-Proxy.md)

Defines Playwright reliability rules for proxied Next.js API flows.

### [ADR-032 – Handling Next.js Router Cache Race Conditions](./ADR-032-Handling-Next.js-Router-Cache-Race-Conditions.md)

Defines SSR/CSR boundary rules for user-specific header widgets and cart badge updates.

### [ADR-034 – SSR Hydration Race Condition with Controlled Form Inputs](./ADR-034-SSR-Hydration-Race-Condition-with-Controlled-Form-Inputs.md)

Prefers uncontrolled inputs for simple SSR forms to avoid hydration overwrite races.

---

## Deployment, Runtime, and Delivery Process

### [ADR-021 – Pre-1.0 Migration Reset Policy](./ADR-021-Pre-1.0-Migration-Reset-Policy.md)

Allows controlled migration resets before 1.0 for foundational schema changes.

### [ADR-028 – Delivery Model Adjustment: Scrum to Scrumban (XP-driven)](./ADR-028-Delivery-Model-Adjustment-XP-Scrumban.md)

Formally adopts Scrumban/XP-style delivery to handle discovery-driven technical work.

### [ADR-048 – Demo Deployment Architecture](./ADR-048-Demo-Deployment-Architecture.md)

Defines the public demo deployment as a multi-service runtime architecture.

---

## Working Rules for ADRs

- Accepted ADRs with runtime impact should be reflected in the **Current Architecture Baseline**.
- If a new cross-cutting finding changes an existing invariant, create:
  - a new ADR, or
  - an explicit update/superseding ADR.
- ADRs should describe **why** and **trade-offs**, not duplicate code-level implementation details.

---

## Reading by Topic

### Pricing / Commerce

ADR-006, 013, 039, 040, 041, 042, 043, 044

### Identity / Authentication

ADR-019, 020, 022, 023, 030, 033, 035, 036

### Cart / Checkout

ADR-008, 018, 022, 023, 026, 033

### Inventory / Fulfillment / Shipping

ADR-017, 025, 029, 047

### Payments

ADR-045, 046

### Frontend Integration / SSR / E2E

ADR-027, 030, 031, 032, 034

### Process / Delivery / Deployment

ADR-021, 028, 048

## Notes

- ADRs explain why decisions were made.
- Some ADRs describe process decisions (CI, testing workflow) where they directly impact system quality.
- The [Architecture Baseline](../architecture/Current%20Architecture%20Baseline.md) reflects the current, effective state derived from accepted ADRs.
