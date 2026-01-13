# ADR-025: Inventory Reservation Model (Reserve on Checkout, Commit on Payment)

**Decision type**: Architecture

**Status**: Accepted

**Date**: Sprint 9

**Related**:

[ADR-017](./ADR-017-Inventory-Reservation-and-Order-Status-Policy.md) (Inventory & Order Status Policy),

[ADR-014](./ADR-014-Dual-Database-Testing-Strategy.md) (Dual DB Testing),

[ADR-021](./ADR-021-Pre-1.0-Migration-Reset-Policy.md) (Pre-1.0 Migration Reset),

[ADR-022](./ADR-022-Anonymous_Cart_Introduction.md) (Anonymous Cart),

[ADR-023](./ADR-023-Guest-Checkout-and-Verified-Claim-of-Guest-Orders.md) (Guest Checkout)

## Context

The system supports guest checkout and creates orders before payment is completed. To prevent overselling and to support realistic fulfillment flows, we need a deterministic inventory model that separates:

- **holding stock** (temporary reservation)
- **committing stock** (final stock decrement after successful payment)

Additionally, the design should remain future-friendly for potential external warehouse/WMS integration without introducing multi-tenant complexity pre-1.0.

## Decision

We introduce an explicit **InventoryReservation** entity and adopt the following inventory policy:

1. **Reserve on checkout**: when an order is created at checkout, stock is reserved per ordered product.
2. **Commit on payment success**: when payment succeeds, reserved stock is committed by decrementing product physical stock.
3. **Release on cancellation or expiry**: reservations are released if the order is cancelled or reservation TTL expires.
4. `Product.stock_quantity` represents physical stock (source of truth for on-hand inventory inside this system).

### Stock semantics (invariant)

- `Product.stock_quantity` is physical stock on hand.
- Availability for reservation is computed as:

  `available = stock_quantity - sum(active_reservations.quantity for product)`

Active reservations are those with status = ACTIVE and expires_at > now.

### Reservation model

We add a new table: `InventoryReservation`:

- `order` (FK)
- `product` (FK)
- `quantity` (int)
- `status` (`ACTIVE | COMMITTED | RELEASED`)

  (Optional: if `EXPIRED` is used, it must be terminal and treated as a release with reason `PAYMENT_EXPIRED`.)

- `expires_at` (datetime, TTL)
- `committed_at`, `released_at` (datetime, nullable)
- `release_reason` (TextChoices, e.g. `PAYMENT_FAILED`, `PAYMENT_EXPIRED`, `CUSTOMER_REQUEST`, `ADMIN_CANCEL`, `OUT_OF_STOCK`)
- **Uniqueness**: (`order, product`) is unique (one row per product per order)

### Order cancellation metadata (audit-friendly MVP)

To support traceability before a full audit log exists, orders include:

- `cancel_reason` (TextChoices)
- `cancelled_by` (CUSTOMER | ADMIN | SYSTEM)
- `cancelled_at`

This is a lightweight summary and does not replace audit logging (see future work).

## Service Layer Guardrails

All inventory and status side effects must be executed via service layer operations. Models remain “dumb” (no side effects in `save()`, no signals).

Required service operations:

1. `reserve_for_checkout(order, ttl=None)`

   - transactional (`transaction.atomic`)
   - locks product rows using `select_for_update()` in stable order (sorted product ids)
   - computes availability: `stock_quantity - active_reserved_sum`
   - creates/updates reservations to `ACTIVE` with `expires_at = now + TTL`
   - raises a domain conflict error if any product lacks availability

2. `commit_reservations_for_paid(order, actor_context=None)`

   - transactional and idempotent
   - locks reservation rows + product rows
   - decrements `Product.stock_quantity` by reserved quantities
   - transitions reservations `ACTIVE → COMMITTED` with `committed_at`
   - transitions order `CREATED → PAID`
   - if invoked multiple times, must not double-decrement

3. `release_reservations(order, reason, actor_context=None)`

   - transactional and idempotent
   - transitions reservations `ACTIVE → RELEASED` with `released_at` and `release_reason`
   - for orders in `CREATED`, transitions order to `CANCELLED` with cancellation metadata
   - **does not restock**, because stock was not decremented during reservation

4. `expire_overdue_reservations(now=timezone.now())`

   - background job / scheduled runner
   - finds `ACTIVE` reservations with `expires_at < now` and releases them with reason `PAYMENT_EXPIRED`
   - cancels the associated order if still `CREATED`
   - idempotent under repeated execution

## API & Error Contract

- Inventory errors use the unified error payload.
- Insufficient stock during reservation must return HTTP **409 Conflict** with a stable domain error code (e.g. `OUT_OF_STOCK`).
- No inventory logic is implemented directly in views; views call service functions.

## Concurrency & Testing

- SQLite is used for fast unit tests of business logic and TTL rules.
- MySQL verification tests (marked `@pytest.mark.mysql`) are required for:
  - concurrent reserve on last stock (exactly one succeeds)
  - multi-product reserve with stable lock ordering (no deadlocks)
  - commit vs expire/cancel races (idempotent under contention)

## Consequences

**Positive**

- Prevents overselling deterministically.
- Provides an audit-friendly reservation trail.
- Enables future external fulfillment/WMS integration without redesigning order models.
- Keeps orchestration testable and maintainable.

**Negative / Trade-offs**

- More DB writes and queries (reservations + aggregates).
- Requires careful transactional locking and MySQL verification tests.
- TTL expiration requires a scheduled job.

## Future Work (out of scope)

- Full audit log MVP for inventory events and order status changes.
- External WMS integration adapter (ports/adapters), SKU mapping, inbound/outbound webhooks.
- Denormalized reserved counters for performance (if needed).
