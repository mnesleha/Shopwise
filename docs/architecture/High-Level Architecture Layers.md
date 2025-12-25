# High-Level Architecture Layers

Shopwise is a backend-focused, monorepo-based system designed around
explicit domain workflows and quality-driven development practices.

At a high level, the system consists of:

- Domain layer (business rules and invariants)
- API layer (workflow orchestration)
- Persistence layer (relational database)
- Testing layer (automated verification)
- Documentation layer (knowledge and quality support)

## Component Overview

### Domain Layer

The domain layer contains the core business concepts and rules.

Key responsibilities:

- enforce invariants (e.g. cart state, item validity)
- represent business intent and outcomes
- remain independent of transport concerns

Primary domain concepts are documented in:

- [Domain Model](Domain%20Model.md)
- [Cart-Order Lifecycle](./Cart-Order%20Lifecycle.md)

### API Layer

The API layer exposes domain workflows via REST endpoints.

Responsibilities:

- authenticate and authorize requests
- orchestrate domain operations
- translate domain outcomes into HTTP responses

The API is intentionally workflow-oriented rather than CRUD-oriented.

### Persistence Layer

Shopwise uses a relational database to persist domain state.

- SQLite is used for tests and CI
- MySQL is used for local and production-like environments

Database concerns are kept separate from domain rules whenever possible.

### Testing Layer

Testing is treated as a first-class system component.

The test suite includes:

- unit tests for domain rules
- API integration tests for workflows and permissions
- E2E tests (Postman) for realistic scenarios

Tests are designed to validate behavior, not implementation details.

### Documentation Layer

Documentation is an integral part of the system architecture.

It serves to:

- explain intent and design decisions
- support onboarding
- reveal quality and coverage gaps

Documentation is structured and maintained alongside the codebase.

## Interaction Overview

A typical request flow:

1. Client sends API request
2. API layer validates permissions
3. Domain layer executes business logic
4. Persistence layer stores state changes
5. API layer returns response
6. Tests and documentation define expected behavior

## Non-Goals

This system overview intentionally does not:

- describe individual endpoints
- document database schemas
- explain testing or documentation tools in detail

Those topics are covered in dedicated documents.

## Summary

Shopwise is structured to emphasize:

- clear domain boundaries
- explicit workflows
- strong testing and documentation practices

This overview provides a map of the system,
while detailed documents provide depth where needed.
