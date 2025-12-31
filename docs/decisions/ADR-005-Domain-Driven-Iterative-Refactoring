# ADR-005: Domain-Driven Iterative Refactoring (Cart → Checkout → Order)

**Status**: Accepted

**Date**: Sprint 6

## Context

Backlog grew to the point where:

- cross-domain solutions led to chaos
- cart domain contained the most bugs, edge cases, and ambiguities
- tests and refactoring blocked each other

## Decision

Go across domains, not horizontally.

- One domain = one iteration:
  - Postman tests (behavior)
  - pytest tests (logic & regression)
  - error handling
  - refactoring
- Sprint 6 was fully dedicated to Cart + Checkout
- Other domains (Orders, Payments, Products) postponed

## Consequences

**Positive**

- Significant reduction in mental load
- Possibility to really go in depth (pricing, rollback, race conditions)
- Better basis for future regression tests

**Negative**

- Other parts of the system not addressed in the short term
- Higher concentration of changes in one area (larger refactor)
