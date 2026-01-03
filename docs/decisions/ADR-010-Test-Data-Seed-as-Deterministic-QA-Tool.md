# ADR-007: Test Data Seed as Deterministic QA Tool

**Status**: Accepted

**Date**: Sprint 7

**Decision type**: Architecure

## Context

Manual work with DB:

- little data
- unstable tests
- impossibility of CI automation

## Decision

Introduced deterministic seed:

- Management command
- `--reset` flag:
  - deletes carts, orders, payments
  - preserves superuser
- Fixed users (username = password)
- Seed connected to pytest session fixture

## Consequences

**Positive**

- Stable testing environment
- Less manual work
- Basis for CI

**Negative**

- Tests must take into account existing data
- Need for strict test isolation
