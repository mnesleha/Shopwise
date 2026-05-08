# Shopwise Documentation

Welcome to the documentation for **Shopwise** — a quality-driven commerce showcase project evolving toward a **marketable e-commerce starter kit**.

This documentation is intentionally curated to support three goals:

- explain the product and architectural direction
- document the current system truth
- make the project reviewable as an engineering showcase

---

## Recommended Reading Order

If you are new to the project, start here:

1. [Onboarding](./Onboarding.md)
2. [Product Vision](./vision/Product%20Vision.md)
3. [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
4. [ADR Index](./decisions/readme.md)
5. [Test Strategy](./testing/Test%20Strategy.md)

---

## Documentation Sections

### Vision

Product-level intent and the quality characteristics the project is optimizing for.

- [Product Vision](./vision/Product%20Vision.md)
- [Quality Goals](./vision/Quality%20Goals.md)

### Demo Scenarios

Narrative walkthroughs of the most important implemented business flows.

- [Demo scenarios index](./demo/readme.md)

### API

API contract documentation and OpenAPI references.

- [OpenAPI](./api/OpenAPI.md)

### Architecture

High-level architecture, current system truth, domain structure, and lifecycle behavior.

- [System Architecture Overview](./architecture/System%20Architecture%20Overview.md)
- [Current Architecture Baseline](./architecture/Current%20Architecture%20Baseline.md)
- [Domain Model](./architecture/Domain%20Model.md)
- [ER Diagram](./architecture/ER%20diagram.md)
- [Cart–Order Lifecycle](./architecture/Cart-Order%20Lifecycle.md)
- [Inventory Reservation Lifecycle](./architecture/Inventory%20Reservation%20Lifecycle.md)
- [Postman Anonymous Cart Testing](./architecture/Postman%20Anonymous%20Cart%20Testing.md)

### ADRs

Historical record of important architectural and process decisions.

- [Architectural Decisions Index](./decisions/readme.md)

### Testing

Current layered testing strategy and quality validation model.

- [Test Strategy](./testing/Test%20Strategy.md)

### Process

Delivery and quality-working rules used in the project.

- [Working Agreement](./process/Working%20Agreement.md)
- [Sprint Process](./process/Sprint%20Process.md)
- [Definition of Done](./process/Definition%20of%20Done.md)
- [QA in Development](./process/QA%20in%20Development.md)

### CI/CD

Pipeline structure and current CI/CD execution model.

- [Pipeline Overview](./ci-cd/Pipeline%20Overview.md)

---

## Documentation Rules

- **Current Architecture Baseline** describes what is true now.
- **ADRs** explain why important decisions were made.
- **Test Strategy** explains how quality is currently validated.
- **Deep-dive documents** should add detail, not duplicate the baseline.
- If an accepted ADR changes runtime behavior, the baseline should be updated.

---

## Notes

This documentation is intentionally selective.

Documents that were outdated, redundant, or too implementation-specific for the public documentation surface were removed from navigation in order to keep the documentation:

- easier to review
- more trustworthy
- more presentation-ready
