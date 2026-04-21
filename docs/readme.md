# Shopwise Documentation

This directory contains the living documentation for the **Shopwise** project.

Shopwise is a QA/SDET-focused showcase project evolving toward a **marketable e-commerce starter kit**.  
The documentation is intentionally split into:

- **current-state documents** — what is true now
- **decision records** — why the system was shaped this way
- **deep-dive architecture and testing documents** — how specific areas work
- **process and delivery documents** — how the project is developed

---

## Start Here

### 1. [Onboarding](./Onboarding.md)

The best starting point for understanding the project context, workflow, quality strategy, and how to navigate the documentation.

### 2. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)

The authoritative snapshot of the current system architecture.  
Read this first if you want to understand how Shopwise works **today**.

### 3. [ADR Index](./decisions/readme.md)

Architecture and process decision log.  
Read this to understand **why** the system looks the way it does.

---

## Documentation Structure

### Architecture

Architecture documents describe the current system design, domain boundaries, runtime flows, and implementation guardrails.

- [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
- [System Architecture Overview](./architecture/System%20Architecture%20Overview.md)
- [Domain Model](./architecture/Domain%20Model.md)
- [ER Diagram](./architecture/ER%20diagram.md)
- [Architecture & Quality Guard Rules](./architecture/Architecture%20%26%20Quality%20Guard%20Rules.md)

#### Core domain flow documents

- [Cart–Order Lifecycle](./architecture/Cart-Order%20Lifecycle.md)
- [Inventory Reservation Lifecycle](./architecture/Inventory%20Reservation%20Lifecycle.md)

#### Testing / integration architecture

- [Postman CLI in CI](./architecture/Postman%20CLI%20in%20CI.md)
- [Postman Anonymous Cart Testing](./architecture/Postman%20Anonymous%20Cart%20Testing.md)

---

### Decisions

Decision records capture significant architectural and process choices.

- [ADR Index](./decisions/readme.md)

Use ADRs to understand:

- API contract decisions
- identity and authentication strategy
- cart / checkout / order model evolution
- inventory and fulfillment model
- payments and shipping provider abstractions
- testing strategy and delivery process
- deployment/runtime trade-offs

---

### Testing & Quality

Testing documents describe the quality strategy, test pyramid, CI validation, and E2E boundaries.

- [Test Strategy](./testing/Test%20Strategy.md)
- [Test Pyramid](./testing/Test%20Pyramid.md)
- [Coverage vs Risk](./testing/Coverage%20vs%20Risk.md)
- [E2E Postman](./testing/E2E%20Postman.md)
- [Quality Discovery](./testing/Quality%20Discovery.md)

---

### Process

Process documents describe how the project is delivered and how quality is enforced in day-to-day development.

- [Working Agreement](./process/Working%20Agreement.md)
- [Sprint Process](./process/Sprint%20Process.md)
- [Workflow](./process/Workflow.md)
- [Definition of Done](./process/Definition%20of%20Done.md)
- [QA in Development](./process/QA%20in%20Development.md)

---

### CI / CD

CI/CD documentation explains pipeline structure, quality gates, and deployment validation.

- [Pipeline Overview](./ci-cd/Pipeline%20Overview.md)
- [Quality Gates](./ci-cd/Quality%20Gates.md)

---

### Vision / Product

Vision documents explain the product intent, business direction, and quality goals.

- [Product Vision](./vision/Product%20Vision.md)
- [Business Goals](./vision/Business%20Goals.md)
- [Quality Goals](./vision/Quality%20Goals.md)
- [Requirements](./vision/Requirements.md)

---

## Recommended Reading Paths

### New contributor / reviewer

1. [Onboarding](./Onboarding.md)
2. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
3. [ADR Index](./decisions/readme.md)
4. [Cart–Order Lifecycle](./architecture/Cart-Order%20Lifecycle.md)
5. [Test Strategy](./testing/Test%20Strategy.md)

### Backend / API work

1. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
2. Relevant ADRs from the [ADR Index](./decisions/readme.md)
3. Domain flow documents
4. Testing and CI documents

### Frontend integration work

1. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
2. Relevant auth / SSR / API contract ADRs
3. Domain flow documents
4. E2E and testing architecture documents

### Architecture review

1. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
2. [ADR Index](./decisions/readme.md)
3. [System Architecture Overview](./architecture/System%20Architecture%20Overview.md)
4. Domain flow documents

---

## Documentation Rules

- **Current Architecture Baseline** describes what is true now.
- **ADRs** explain why important decisions were made.
- If an accepted ADR changes system behavior, the baseline should be updated accordingly.
- Deep-dive documents should describe one topic well instead of duplicating the baseline.

---

## Project Documentation Philosophy

The documentation is intentionally treated as part of the system design.

It aims to be:

- **practical** — useful during implementation and review
- **traceable** — linked to decisions and code behavior
- **test-aware** — aligned with the project’s QA/SDET focus
- **presentable** — suitable for portfolio / CV showcase use
