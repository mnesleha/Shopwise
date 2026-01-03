# ADR-007: Atomic Checkout with Explicit Rollback Guarantees

**Status**: Accepted

**Date**: Sprint 7 (Hardening)

**Decision type**: Architecure

## Context

Checkout was a critical point:

- risk of partial state (order created, cart not)
- race conditions (double checkout)
- missing rollback scenarios

## Decision

- Checkout is a fully atomic operation:
  - `transaction.atomic`
  - `select_for_update()` on Cart
- Cart state checked after lock
- Cart status changed only after successful order + items creation
- On any error:
  - rollback DB
  - cart remains ACTIVE
  - no order exists

## Consequences

**Positive**

- Data consistency
- Elimination of ghost orders
- Ready for real-world competition

**Negative**

- More complex testing (rollback scenarios)
- SQLite has limitations (need transaction=True in pytest)
