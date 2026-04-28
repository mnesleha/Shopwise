# System Architecture Overview

## Purpose

This document provides a high-level overview of the Shopwise system architecture.

It explains:

- the major runtime building blocks
- how core domains interact
- how the system is deployed
- where the main architectural boundaries are

For the **authoritative current runtime truth**, see:

- [Current Architecture Baseline](./Current%20Architecture%20Baseline.md)

For historical design rationale, see:

- [ADR Index](../decisions/readme.md)

---

## 1. System at a Glance

Shopwise is a quality-driven commerce application built as a **QA/SDET showcase project** and evolving toward a **marketable e-commerce starter kit**.

It is designed around these principles:

- backend-owned business logic
- explicit domain boundaries
- provider-agnostic external integrations
- snapshot-based historical truth
- strong automated testing across layers
- architecture and documentation as first-class engineering artifacts

---

## 2. High-Level Runtime Architecture

The current public demo is deployed as a **multi-service architecture**.

### Main runtime components

- **Frontend**
  - Next.js application
  - SSR + CSR hybrid rendering
  - deployed on Vercel

- **Backend API**
  - Django + Django REST Framework
  - public API and domain orchestration
  - deployed as Render web service

- **Background Worker**
  - django-q2 worker process
  - asynchronous jobs and email handling
  - deployed separately from the web service

- **Database**
  - MySQL
  - source of runtime persistence truth

- **Media Storage**
  - Cloudflare R2
  - product and editorial media storage

- **Supporting Services**
  - AcquireMock (payment provider mock)
  - mock shipping provider
  - Mailpit (demo/development email preview)

---

## 3. Runtime Component Diagram (Conceptual)

```text
Frontend (Next.js / Vercel)
        |
        v
Backend API (Django / DRF / Render)
        |
        +--> MySQL (Aiven)
        |
        +--> R2 Media Storage
        |
        +--> Background Worker (django-q2 / Render)
        |
        +--> AcquireMock (payment provider mock)
        |
        +--> Mock Shipping Provider
        |
        +--> Mailpit
```

This separation is intentional:

- frontend is independent from backend deployment
- async work is not coupled to web request handling
- provider mocks are externalized as integration boundaries
- storage and database are separate infrastructure concerns

---

## 4. Core Domain Areas

The current system is organized around several core business domains.

### 4.1 Identity & Account

Responsible for:

- user registration
- authentication
- session state
- guest-to-user transitions
- email verification
- account security operations

Key characteristics:

- custom user model
- email-based identity
- JWT in httpOnly cookies
- SSR-compatible auth integration

---

### 4.2 Catalogue

Responsible for:

- product listing and detail
- category organization
- media references
- search

Key characteristics:

- flat category model
- backend-owned media URLs
- MySQL-based search backend abstraction

---

### 4.3 Cart

Responsible for:

- mutable shopping intent
- anonymous and authenticated cart flows
- cart merge/adopt behavior
- cart state used before checkout

Key characteristics:

- authenticated carts resolved via ActiveCart pointer
- anonymous carts resolved via token
- merge/adopt rules are deterministic and testable

---

### 4.4 Checkout & Orders

Responsible for:

- checkout orchestration
- immutable order snapshots
- guest checkout
- guest order claiming
- order state management

Key characteristics:

- checkout creates the order before payment completion
- orders preserve historical truth via snapshots
- guest orders may later be claimed by verified users

---

### 4.5 Inventory

Responsible for:

- stock reservation
- stock commitment after successful payment
- release on cancellation or expiration
- preventing overselling

Key characteristics:

- physical stock is explicit
- reservation is modeled separately from stock decrement
- inventory behavior is service-layer orchestrated

---

### 4.6 Payments

Responsible for:

- payment initiation
- provider abstraction
- hosted payment flow handling
- provider callback processing
- applying confirmed payment outcomes

Key characteristics:

- provider-agnostic architecture
- backend-confirmed payment truth
- AcquireMock as first provider
- frontend return flow is not payment authority

---

### 4.7 Shipping / Fulfillment

Responsible for:

- shipment creation
- shipment status lifecycle
- provider-specific shipping integration boundary
- projecting shipment truth to business-visible order state where useful

Key characteristics:

- carrier-agnostic architecture
- first provider is a mock/manual provider
- shipping is separated from payment and inventory truth

---

### 4.8 Audit & Operational Traceability

Responsible for:

- mmutable audit events
- domain event traceability
- support for troubleshooting and future integrations

Key characteristics:

- separate audit domain/app
- best-effort logging model
- emitted from service layer only

---

## 5. Main Interaction Flows

### 5.1 Customer Journey (Simplified)

```text
Catalogue -> Cart -> Checkout -> Order Created -> Payment -> Order Paid -> Shipment -> Delivery
```

#### Important architectural notes

- Cart is mutable
- Order is immutable snapshot
- Payment success is backend-confirmed
- Inventory is reserved before payment and committed after payment
- Shipping begins only after payment-complete state

---

### 5.2 Guest Flow

Guest users can:

- browse catalogue
- create anonymous cart
- checkout without account
- receive guest order emails
- later claim eligible orders through verified identity flow

This enables realistic low-friction commerce behavior.

---

### 5.3 Authenticated Flow

Authenticated users can:

maintain a current cart
merge/adopt guest cart on login
access order/account pages through SSR-compatible auth flow
perform account-level identity operations

---

## 6. Architectural Boundaries

The following boundaries are intentionally enforced.

### Backend vs Frontend

- backend owns business truth
- frontend renders and interacts with backend-produced state
- frontend must not compute authoritative pricing, payment truth, or shipment truth

### Domain logic vs Infrastructure

- service layer orchestrates domain side effects
- external systems are accessed through adapters or dedicated service boundaries

### Core system vs External Providers

- payment/shipping providers are replaceable implementations
- provider-specific payloads are normalized before entering core logic

### Current truth vs Historical truth

- catalogue and pricing data are mutable runtime state
- orders preserve explicit snapshots for historical accuracy

---

## 7. Data and State Strategy

The system combines mutable runtime state with immutable historical state.

### Mutable runtime state

- cart contents
- active cart pointer
- reservations
- payment attempts/status
- shipment status
- account/session state

### Historical / snapshot state

- order items
- order pricing
- tax/promotion effects at order time
- shipping selection snapshot
- audit events

This separation allows:

- reliable order history
- safe future refactors of pricing/promotions/catalogue
- explainable business behavior over time

---

## 8. Integration Strategy

The current architecture is designed to be **integration-friendly**.

### Payment provider integration

Provider-specific initiation and callback handling is isolated behind payment provider adapters.

### Shipping provider integration

Carrier-specific status flows are isolated behind shipment provider adapters.

### Media storage integration

Storage is abstracted behind Django storage configuration.

### Future external systems

The architecture leaves space for:

- real payment gateways
- real shipping carriers
- WMS / ERP-like extensions
- richer observability sinks

without forcing those concerns into core business models too early.

---

## 9. Security and Reliability Characteristics

The current architecture includes these notable runtime characteristics:

- JWT in httpOnly cookies
- SSR-safe cookie forwarding
- throttling for abuse-prone flows
- explicit audit trail for critical business operations
- idempotent handling of payment and shipping side effects
- MySQL verification for concurrency-sensitive logic
- Playwright and API contract testing for cross-layer reliability

---

## 10. Deployment Characteristics

The public demo is intentionally deployed in a way that reflects actual runtime concerns:

- frontend and backend are independently deployable
- worker runs separately
- provider mocks are separate services
- media is externalized
- demo depends on deterministic seed data
- operational diagnosis is boundary-aware and log-driven

This is important for the showcase aspect of the project:
the deployment demonstrates not just “working code”, but also realistic system operation.

---

## 11. CI/CD and Documentation

The project uses **GitHub Actions** as its CI/CD execution layer.

Current workflows validate backend quality, browser-based frontend flows, and documentation publishing.
CI/CD is treated as part of the system’s quality architecture, not merely as build automation.

Project documentation is written in **Markdown** and published using **MkDocs**.
Documentation is treated as a first-class engineering artifact:
the Current Architecture Baseline describes current truth, while ADRs preserve decision history.

---

## 12. What This Document Does Not Try to Do

This document is intentionally high-level.

It does not replace:

- [Current Architecture Baseline](./Current%20Architecture%20Baseline.md) for exact current truth
- ADRs for decision rationale
- lifecycle-specific documents for detailed flow behavior
- testing documents for test strategy and quality gates

Use it as the architectural “big picture”, not as a low-level implementation reference.

---

## 13. Related Documents

### Core references

- [Current Architecture Baseline](./Current%20Architecture%20Baseline.md)
- [ADR Index](../decisions/readme.md)

### Domain flow documents

- [Cart–Order Lifecycle](./Cart-Order%20Lifecycle.md)
- [Inventory Reservation Lifecycle](./Inventory%20Reservation%20Lifecycle.md)

### Testing / quality

- [Architecture & Quality Guard Rules](./Architecture%20&%20Quality%20Guard%20Rules.md)
- [Test Strategy](../testing/Test%20Strategy.md)

### Onboarding

- [Onboarding](../Onboarding.md)
