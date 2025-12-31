# ADR-008: Double Checkout Protection via Row Locking

**Status**: Accepted

**Date**: Sprint 7

## Context

There was a risk of:

- two parallel checkouts
- creating multiple orders from one cart

## Decision

Protection implemented:

- `select_for_update()` on Cart
- Check `cart.status` after locking
- If not ACTIVE → 409 Conflict
- We do not implement non-deterministic concurrency tests (SQLite ≠ MySQL)

## Consequences

**Positive**

- Deterministic behavior
- Clear business contract
- Testable sequentially

**Negative**

- Real concurrency test postponed to performance sprint
