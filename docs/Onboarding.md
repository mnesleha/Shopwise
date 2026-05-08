# Onboarding

## Purpose

This document is the recommended entry point for understanding the **Shopwise** project.

It explains:

- what Shopwise is today
- how the project is structured
- how to navigate the documentation
- what the main architectural and quality principles are
- where to start depending on your role or review goal

This document is intentionally practical.  
It does not try to be the full architecture reference.

For the authoritative current system truth, see:

- [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)

For historical design rationale, see:

- [ADR Index](./decisions/readme.md)

---

## 1. What Shopwise Is

**Shopwise** is a quality-driven commerce application built as a **QA/SDET showcase project** and evolving toward a **marketable e-commerce starter kit**.

The project exists to demonstrate not only feature delivery, but also:

- architectural thinking
- explicit decision-making
- strong automated testing
- realistic runtime boundaries
- documentation as part of engineering quality

It is intentionally more than a toy demo or CRUD showcase.
The project aims to show how a modern commerce system can be built with:

- backend-owned business logic
- explicit domain boundaries
- safe evolution over time
- reliable automated verification
- presentable, reviewable documentation

---

## 2. Current Shape of the System

Shopwise is currently a **multi-part system**, not a backend-only application.

### Main parts

- **Frontend** — Next.js, React, TypeScript
- **Backend API** — Django + Django REST Framework
- **Background worker** — django-q2
- **Database** — MySQL
- **Media storage** — Cloudflare R2
- **Supporting services** — payment provider mock, shipping provider mock, Mailpit
- **Public demo deployment** — Vercel + Render + Aiven + R2

The project includes both:

- backend architecture work
- frontend integration work

It is already deployed as a public multi-service demo.

---

## 3. What the Project Currently Covers

The current implemented scope includes:

- catalogue browsing
- anonymous cart
- authenticated cart
- cart merge/adopt behavior on login
- checkout
- guest checkout
- guest order claiming after verified email
- inventory reservation and release
- payment orchestration with provider abstraction
- shipping orchestration with provider abstraction
- async email delivery
- public demo deployment

The project is currently also evolving in:

- pricing / VAT / promotions
- frontend integration guard
- marketable v1.0 scope shaping

---

## 4. How to Read This Documentation

The documentation is intentionally split into several layers.

## 4.1 Start with these documents

### [Product Vision](./vision/Product%20Vision.md)

Explains why the project exists and what direction it is taking.

### [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)

Describes what is true now.

### [ADR Index](./decisions/readme.md)

Explains why important decisions were made.

### [Test Strategy](./testing/Test%20Strategy.md)

Explains how system behavior is validated.

---

## 4.2 Documentation roles

### Vision documents

Explain:

- why the project exists
- what qualities matter most
- what direction the product is taking

### Architecture documents

Explain:

- current runtime structure
- domain boundaries
- lifecycle behavior
- implementation guardrails

### ADRs

Explain:

- why a decision was made
- what trade-offs were accepted
- how architectural evolution happened

### Testing documents

Explain:

- how quality is verified
- what each test layer is responsible for
- how testing aligns with architecture

### CI/CD documents

Explain:

- how validation and documentation publishing are automated

---

## 5. Core Architectural Truths

These are the most important things to understand early.

### 5.1 Backend is the business authority

The backend is the authoritative source of truth for:

- pricing
- inventory
- orders
- payment outcomes
- shipping state
- audit events

Frontend never computes authoritative business results.

### 5.2 Service layer owns side effects

Business side effects belong in service-layer orchestration, not in views, serializers, or model `save()` hooks.

### 5.3 Orders preserve historical truth

Orders are snapshot-based.  
History must not be rebuilt from mutable runtime catalogue or pricing state.

### 5.4 External integrations are isolated

Payments and shipping providers are isolated behind provider adapters.
The core system should not depend on provider-specific payload structure.

### 5.5 Testing is an architecture tool

Tests are used not only to detect regressions, but also to enforce domain invariants, verify concurrency behavior, and validate architectural boundaries.

---

## 6. Core Domain Areas

## 6.1 Identity & Authentication

Covers:

- registration
- login
- JWT in httpOnly cookies
- session probing
- verified identity flows
- secure account operations

## 6.2 Catalogue

Covers:

- products
- flat categories
- media references
- search behavior

## 6.3 Cart

Covers:

- authenticated cart resolution via ActiveCart pointer
- anonymous cart token flow
- merge/adopt behavior on login

## 6.4 Checkout & Orders

Covers:

- order creation
- immutable order snapshots
- guest checkout
- guest order claiming

## 6.5 Inventory

Covers:

- reserve on checkout
- commit on payment success
- release on cancel / expiry
- physical stock semantics

## 6.6 Payments

Covers:

- provider-agnostic payment architecture
- hosted payment initiation
- backend-confirmed payment truth

## 6.7 Shipping

Covers:

- carrier-agnostic shipping architecture
- shipment lifecycle
- mock/manual provider as first implementation

## 6.8 Audit

Covers:

- append-only audit event trail
- best-effort event persistence
- service-layer emission

---

## 7. Testing and Quality Model

Shopwise uses a layered test strategy.

### Backend / domain correctness

- `pytest`

### MySQL verification

- MySQL-specific correctness and concurrency tests

### API contract / workflow validation

- Postman

### Frontend validation

- Vitest

### Browser E2E

- Playwright

### Performance baseline

- Locust

### CI/CD execution

- GitHub Actions

Testing is intentionally separated by responsibility rather than collapsed into one large undifferentiated test layer.

For detail, see:

- [Test Strategy](./testing/Test%20Strategy.md)

---

## 8. Delivery Model

The project currently uses:

- **Scrumban** as the practical delivery model
- **XP / TDD / documentation-driven development** as the technical core

This reflects the realities of:

- solo development
- architecture-heavy discovery
- strong test-driven refinement
- frequent cross-cutting findings

Architectural evolution is expected, but it should always be captured explicitly in ADRs and reflected in the current baseline.

---

## 9. Recommended Reading Paths

## 9.1 Recruiter / reviewer

1. [README (root)](../README.md)
2. [Product Vision](./vision/Product%20Vision.md)
3. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
4. [ADR Index](./decisions/readme.md)

## 9.2 Backend contributor

1. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
2. Relevant ADRs from the [ADR Index](./decisions/readme.md)
3. [Cart–Order Lifecycle](./architecture/Cart-Order%20Lifecycle.md)
4. [Inventory Reservation Lifecycle](./architecture/Inventory%20Reservation%20Lifecycle.md)
5. [Test Strategy](./testing/Test%20Strategy.md)

## 9.3 Frontend contributor

1. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
2. Relevant auth / SSR / E2E ADRs
3. [System Architecture Overview](./architecture/System%20Architecture%20Overview.md)
4. [Test Strategy](./testing/Test%20Strategy.md)

## 9.4 Architecture reviewer

1. [Product Vision](./vision/Product%20Vision.md)
2. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
3. [System Architecture Overview](./architecture/System%20Architecture%20Overview.md)
4. [ADR Index](./decisions/readme.md)

---

## 10. Active Evolution Areas

The following areas are currently evolving and should be read with awareness that further ADRs may refine them:

- pricing / VAT / promotions
- provider maturity beyond mock providers
- richer deployment/observability practices
- broader audit coverage
- v1.0 scope closure

When reviewing these areas, rely on:

- accepted ADRs
- current baseline
- current test coverage
- current deployed behavior

---

## 11. Final Note

Shopwise is intentionally built as a **serious engineering artifact**.

It is meant to show:

- how architecture evolves under test feedback
- how documentation supports engineering quality
- how domain correctness is protected across backend, API, frontend, and runtime boundaries
- how a commerce system can be made both explainable and testable

If you are new to the project, the best next document to read is:

- [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
