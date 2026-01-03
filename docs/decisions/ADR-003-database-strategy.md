# ADR-003: Database Strategy

**Decision type**: Architecure

## Status

Accepted

## Context

The Shopwise project requires a balance between fast feedback
during development and consistent behavior across environments.

Using a single database system everywhere would simplify consistency,
but would also increase CI complexity and execution time.

## Decision

The project adopts a hybrid database strategy:

- SQLite is used for unit tests
- MySQL is used for integration tests, local development, and production

## Rationale

- Unit tests focus on business logic and require fast execution
- Integration tests validate real database behavior
- MySQL is used where database-specific behavior matters

## Consequences

- Slightly more complex test configuration
- Faster CI feedback for unit tests
- Higher confidence in production behavior
