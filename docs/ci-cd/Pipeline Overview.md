# Pipeline Overview

## Purpose

This document describes the current CI/CD pipeline setup of the Shopwise project.

It explains:

- what workflows currently run in GitHub Actions
- what each workflow validates
- how CI supports architecture and quality goals
- how documentation publishing is integrated into the delivery model

This document describes the **current operational reality**, not an idealized future pipeline.

---

## 1. CI/CD Philosophy

Shopwise uses **GitHub Actions** as its CI/CD execution layer.

The pipeline is intentionally split into multiple workflows instead of one monolithic pipeline.
This keeps responsibilities clear and failures easier to diagnose.

The current pipeline reflects the project’s testing architecture:

- backend/domain validation
- API workflow validation
- frontend validation
- browser E2E validation
- documentation publishing

CI/CD is treated as part of the project’s **quality architecture**, not only as build automation.

---

## 2. Current Workflows

## 2.1 Backend CI

The backend workflow validates backend correctness and API behavior.

### Trigger

- push to active branches
- pull requests to active branches

### Main responsibilities

- install backend dependencies
- run Django migrations
- execute backend pytest suite against SQLite
- execute API-level Postman workflow tests against MySQL
- seed deterministic E2E/API data
- boot the backend in CI for contract/workflow validation
- upload debug artifacts (e.g. JUnit report, runserver log)

### Why it matters

This workflow combines:

- fast backend correctness checks
- realistic API validation
- production-like DB behavior for contract workflows

It reflects the project’s principle that SQLite is sufficient for fast logic feedback, but MySQL is required for realistic verification of DB-sensitive behavior.

---

## 2.2 Frontend Validation

The frontend validation workflow validates frontend-local correctness.

### Trigger

- frontend changes
- related workflow changes
- pull requests affecting frontend

### Main responsibilities

- install frontend dependencies
- run Vitest
- run Next.js production build

### Why it matters

This workflow verifies that the frontend remains:

- buildable
- testable
- syntactically and structurally valid

It is intentionally separate from browser E2E testing.

---

## 2.3 Playwright Browser Tests

The Playwright workflow validates browser-level end-to-end behavior.

### Trigger

- frontend changes
- pull requests affecting frontend

### Main responsibilities

- install Playwright browsers
- run Playwright tests
- upload Playwright HTML report as artifact

### Why it matters

This workflow validates the user-visible integration layer:

- navigation
- SSR/CSR frontend behavior
- browser interaction flows
- critical end-to-end UI scenarios

It complements backend and Postman tests rather than duplicating them.

---

## 2.4 Documentation Deployment

The documentation deployment workflow publishes project documentation.

### Trigger

- push to `main`

### Main responsibilities

- install MkDocs tooling
- build documentation
- deploy documentation via `mkdocs gh-deploy`

### Why it matters

Documentation is treated as a first-class project artifact.
Publishing docs through CI reinforces the idea that documentation is part of the delivery pipeline, not an afterthought.

---

## 3. Workflow Responsibilities by Layer

| Workflow                 | Main purpose                                  |
| ------------------------ | --------------------------------------------- |
| Backend CI               | backend correctness + API workflow validation |
| Frontend Validation      | frontend-local correctness + build validation |
| Playwright Tests         | browser E2E validation                        |
| Documentation Deployment | documentation publishing                      |

This separation intentionally mirrors the system’s testing strategy and runtime architecture.

---

## 4. Backend CI Detail

The backend pipeline currently combines two important validation modes.

### 4.1 Fast backend validation

The pytest suite runs against SQLite for quick feedback on:

- domain logic
- service-layer behavior
- serializers
- model-level behavior that is not DB-engine specific

### 4.2 API workflow validation against MySQL

A separate CI job uses MySQL and runs Postman cloud collection tests against a real backend instance started inside CI.

This includes:

- migration
- deterministic seed data setup
- backend startup
- health verification
- workflow execution via Postman CLI
- JUnit artifact export

This gives the project a stronger contract/integration validation layer than unit tests alone.

---

## 5. Seed Data as Pipeline Dependency

Deterministic seed data is a first-class dependency of the pipeline.

It is used to:

- stabilize API workflow tests
- provide predictable test identities and entities
- support realistic end-to-end validation

This mirrors the broader project principle that seed data is part of system operability, not merely local development convenience.

---

## 6. Artifacts and Diagnostics

The pipeline produces artifacts for diagnosis, including:

- Postman JUnit reports
- backend runserver logs
- Playwright reports

This is important because the project intentionally favors **boundary-aware diagnosis**:
a failure should be traceable to the relevant runtime or validation layer.

---

## 7. Current Trade-offs

The current pipeline intentionally favors **clarity and realism** over minimalism.

### Positive

- clear separation of validation concerns
- realistic MySQL-backed API testing
- browser-level proof of critical UI behavior
- documentation deployment built into the delivery flow

### Trade-offs

- several workflows instead of one compact pipeline
- backend CI is relatively heavy due to seeded MySQL + backend startup
- some branch trigger definitions are not yet fully standardized
- quality gate logic is currently distributed across workflows rather than represented by one explicit orchestrator layer

---

## 8. Current Quality Gate Model

In practice, a change is considered healthy when:

- backend tests pass
- MySQL-backed API workflow validation passes
- frontend validation passes
- Playwright browser tests pass
- documentation deploy/build remains healthy when relevant
- artifacts/logs are sufficient to diagnose failure if one occurs

This project currently treats quality gates as a **distributed validation model** rather than a single monolithic “gatekeeper” workflow.

---

## 9. Planned Evolution Areas

The CI/CD pipeline is expected to evolve further in areas such as:

- branch trigger standardization
- stronger explicit quality gate reporting
- improved workflow naming consistency
- optional future expansion of performance test automation
- possible reduction of documentation overlap between CI and architecture docs

---

## 10. Related Documents

- [Current Architecture Baseline](../architecture/Current%20Architecture%20Baseline.md)
- [System Architecture Overview](../architecture/System%20Architecture%20Overview.md)
- [Test Strategy](../testing/Test%20Strategy.md)
- [Onboarding](../Onboarding.md)
