# Architecture & Process Decision Records (ADR Index)

This index provides an overview of all accepted and proposed decisions in the project.
For the **current system state**, see the [Architecture Baseline document](../architecture/Current%20Architecture%20Baseline.md).

## ADR-001 – Project Setup Decision

Decision type: **Architecture**

Defines the initial layered backend architecture and establishes domain boundaries as the foundation for further development.

[ADR-001](./ADR-001-Project-Setup-Decisions.md)

## ADR-002 - Definition of Done and Process

Decision type: **Process**

Defines Definition of Done and coding/branching principles.

[ADR-002](ADR-002-Definition-of-Done-and-Process.md)

## ADR-003 – Database Strategy (SQLite vs MySQL)

Decision type: **Architecture**

Defines SQLite for fast unit tests and MySQL for production-like behavior, balancing feedback speed and realism.

[ADR-003](ADR-003-Database-Strategy.md)

## ADR-004 – OpenAPI as Source of Truth

Decision type: **Architecture**

Establishes OpenAPI as the authoritative API contract for behavior, status codes, and response structures.

[ADR-004](ADR-004-OpenAPI-as-Source-of-Truth.md)

## ADR-006 – Snapshot Pricing Strategy

Decision type: **Architecture**

Ensures pricing determinism by snapshotting prices and discounts at checkout time.

[ADR-006](ADR-006-Snapshot-Pricing-Strategy.md)

## ADR-007 – Atomic Checkout with Explicit Rollback

Decision type: **Architecture**

Defines checkout as an atomic operation with explicit rollback to prevent partial or inconsistent state.

[ADR-007](ADR-007-Atomic-Checkout-with-Explicit-Rollback.md)

## ADR-008 – Double-Checkout Protection

Decision type: **Architecture**

Prevents converting the same cart multiple times and defines deterministic conflict handling.

[ADR-008](ADR-008-Double-Checkout-Protection.md)

## ADR-009 – Unified Error Handling Strategy

Decision type: **Architecture**

Introduces a unified error payload and centralized exception handling for consistent API behavior.

[ADR-009](ADR-009-Unified-Error-Handling-Strategy.md)

## ADR-012 – Unified Order and Checkout API Contract

Decision type: **Architecture**

Unifies public API response shapes for orders and checkout and removes persistence-specific fields from the contract.

[ADR-012](ADR-012-Unified-Order-and-Checkout-API-Contract.md)

## ADR-013 – Pricing and Rounding Policy

Decision type: **Architecture**

Defines deterministic pricing rules, rounding behavior, and discount precedence (FIXED over PERCENT).

[ADR-013](ADR-012-Unified-Order-and-Checkout-API-Contract.md)

## ADR-014 – Dual Database Testing Strategy

Decision type: **Architecture**

Formalizes the split between SQLite-based unit tests and MySQL-based verification tests for DB-critical behavior.

[ADR-014](ADR-014-Dual-Database-Testing-Strategy.md)

## ADR-015 – Category Model Is Flat

Decision type: **Architecture**

Defines categories as a flat, non-hierarchical model and removes parent/child semantics from the domain and API.

[ADR-015](ADR-015-Category_Model_Is_Flat.md)

## ADR-016 – Postman CLI for API Contract and E2E Testing in CI

Decision type: **Process**

Introduces Postman CLI execution in CI to validate real API workflows against a production-like environment.

[ADR-016](ADR-016-Postman-CLI-for-API-Contract-and-E2E-Testing-in-CI.md)

## Notes

- ADRs explain why decisions were made.
- Some ADRs describe process decisions (CI, testing workflow) where they directly impact system quality.
- The [Architecture Baseline](../architecture/Current%20Architecture%20Baseline.md) reflects the current, effective state derived from accepted ADRs.
