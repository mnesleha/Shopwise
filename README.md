# Shopwise

**The Shopwise development showcase project.**

Shopwise is a demo e-commerce project designed as a **quality-driven showcase**.
Its primary goal is to demonstrate how backend/frontend development, testing, documentation,
and QA processes can work together as equal partners.

The project focuses not only on _what_ is built, but also on _how_ and _why_ it is built:
through architectural decisions, automated testing, documentation, and production-like runtime boundaries.

https://github.com/user-attachments/assets/fd44ec2c-c5c0-4a16-9e2f-85a494b223ad

---

## Why this project exists

Shopwise was created as a **QA/SDET showcase project** and is evolving toward a **marketable e-commerce starter kit**.

It demonstrates:

- realistic domain modeling for commerce flows
- architecture-driven development
- API-first and documentation-aware design
- strong automated testing across multiple layers
- explicit decision-making through ADRs
- quality as a first-class engineering concern

---

## What this project demonstrates

### Product / business flows

- product catalogue
- cart and checkout
- guest checkout
- guest order claiming after verified email
- inventory reservation
- provider-agnostic payments
- carrier-agnostic shipping
- deployment of a public multi-service demo

### Engineering / architecture capabilities

- backend domain design with explicit invariants
- SSR-aware frontend integration
- provider abstraction for payments and shipping
- deterministic pricing and snapshot-based order history
- runtime-ready deployment architecture
- audit-friendly design
- strong use of ADRs and living documentation

### QA / SDET capabilities

- domain-level automated tests
- API contract testing
- browser E2E testing
- concurrency testing against MySQL
- performance baseline testing
- documentation as part of quality governance

---

## Tech Stack

### Application stack

**Backend**

- Python
- Django
- Django REST Framework
- OpenAPI
- MySQL
- SQLite (fast local/unit test workflows)
- django-q2

**Frontend**

- Next.js
- React
- TypeScript
- SSR + CSR hybrid architecture

**Supporting services / infrastructure**

- AcquireMock (payment provider mock)
- mock shipping provider
- Mailpit
- Cloudflare R2
- Aiven MySQL
- Render
- Vercel

---

## Testing & Quality Stack

### Backend / API / domain testing

- **pytest** — unit, service, integration, and concurrency-oriented backend tests
- **Postman** — API workflow and contract validation
- **MySQL verification tests** — race conditions, locking, transactional correctness

### Frontend / E2E testing

- **Vitest** — frontend unit/integration tests
- **Playwright** — browser E2E flows across engines

### Performance / non-functional

- **Locust** — baseline performance and representative traffic testing

---

## What makes Shopwise different from a typical demo project

- It uses **Architecture Decision Records (ADRs)** to explain key design choices.
- It has a **Current Architecture Baseline** document describing the current system truth.
- It treats **testing and documentation as core engineering artifacts**, not add-ons.
- It models realistic runtime concerns:
  - async jobs
  - provider callbacks
  - concurrency
  - deployment boundaries
  - SSR/frontend integration
- It is deployed as a **multi-service public demo**, not a single-process local-only toy app.

---

## Live Demo & Documentation

> Replace the placeholders below with actual public URLs.

- **Live demo:** [`https://shopwise-wine.vercel.app/`](https://shopwise-wine.vercel.app/)
- **GitHub repository:** [`https://github.com/mnesleha/Shopwise`](https://github.com/mnesleha/Shopwise)
- **Documentation entry point:** [`docs/Onboarding.md`](./docs/Onboarding.md)
- **Current Architecture Baseline:** [`docs/architecture/Current Architecture Baseline.md`](./docs/architecture/Current%20Architecture%20Baseline.md)
- **ADR Index:** [`docs/decisions/readme.md`](./docs/decisions/readme.md)

---

## Documentation Map

The `docs/` directory is structured as living project documentation.

Recommended entry points:

- [`docs/Onboarding.md`](./docs/Onboarding.md)
- [`docs/architecture/Current Architecture Baseline.md`](./docs/architecture/Current%20Architecture%20Baseline.md)
- [`docs/decisions/readme.md`](./docs/decisions/readme.md)

If you want to understand the project quickly:

1. Read this README
2. Open the Onboarding document
3. Read the Current Architecture Baseline
4. Browse the ADR index

---

## Current Status

The project is actively developed and already includes the core commerce slice:

- catalogue
- cart
- checkout
- order lifecycle
- payments architecture
- shipping architecture
- guest flows
- async email flows
- deployment of a public demo

Current development focus is on:

- pricing / VAT / promotions evolution
- frontend guard and integration quality
- architectural refinement for marketable v1.0 direction

---

## Repository Structure

- `backend/` — Django backend application
- `frontend/` — Next.js frontend
- `docs/` — architecture, ADRs, testing, process, and project documentation
- `.github/` — CI/CD workflows and automation

---

## Final Note

Shopwise is not intended to be a production-ready enterprise e-commerce platform.

It is intentionally designed as a **serious engineering showcase**:
a project that demonstrates architecture thinking, QA/SDET depth, system design discipline,
and the ability to build software with quality, traceability, and long-term evolution in mind.
