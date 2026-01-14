# Cart–Order Lifecycle

This document describes the current Cart → Order lifecycle in Shopwise,
including inventory reservation, payment interaction, and cancellation semantics.

It reflects the architecture as of Sprint 9 and supersedes earlier snapshots
that relied on direct stock decrement during checkout.

---

## High-Level Principles

- **Cart** represents a mutable shopping intent.
- **Order** represents an immutable snapshot of checkout intent.
- **InventoryReservation** separates _holding stock_ from _physical stock decrement_.
- **Product.stock_quantity** always represents **physical stock only**.
- Stock is decremented **only after successful payment**.
- Time-based expiration is a first-class concept (TTL).

---

## Cart Phase

The cart is a temporary, mutable structure that exists before checkout.

Characteristics:

- Items can be freely added, updated, or removed.
- Cart can be anonymous (guest) or associated with an authenticated user.
- Cart has no impact on inventory availability.

The cart is not persisted as an order until checkout.

---

## Checkout Phase

Checkout transforms a cart into an order snapshot.

At checkout:

- An **Order** is created with status `CREATED`.
- **OrderItems** are created as an immutable snapshot of cart contents.
- **InventoryReservation** records are created for each product in the order.

### Inventory Reservation at Checkout

Checkout does **not** decrement physical stock.

Instead, the system creates inventory reservations with:

- `status = ACTIVE`
- explicit expiration timestamp (`expires_at`)
- quantity per product

Reservation availability is computed as:

available = product.stock_quantity - sum(quantity of ACTIVE reservations for that product)

This prevents overselling under concurrency while keeping physical stock unchanged.

### Reservation TTL

Each reservation has a time-to-live (TTL), applied at checkout time.

TTL values are environment-configurable:

- `RESERVATION_TTL_GUEST_SECONDS`
- `RESERVATION_TTL_AUTH_SECONDS`

The computed TTL is stored directly on the reservation as `expires_at`.

---

## Order Lifecycle

Orders represent a finalized snapshot of checkout intent.

### Order States

Orders can exist in the following states:

- `CREATED`
- `PAID`
- `CANCELLED`

Additional terminal states (planned):

- `SHIPPED`
- `DELIVERED`

### CREATED

- Order was created from checkout.
- Inventory is reserved (`ACTIVE` reservations).
- Physical stock is unchanged.
- Awaiting payment.

### PAID

- Payment completed successfully.
- Inventory reservations are **committed**:
  - reservation status: `ACTIVE → COMMITTED`
  - physical stock is decremented
- Order becomes immutable.

### CANCELLED

- Terminal state.
- Order was not paid or was explicitly cancelled.
- Inventory reservations were released or expired.
- Physical stock remains unchanged.

Cancellation reasons are stored as metadata, not as order states:

- `CUSTOMER_REQUEST`
- `PAYMENT_FAILED`
- `PAYMENT_EXPIRED`
- `OUT_OF_STOCK`
- `SHOP_REQUEST`
- `FRAUD_SUSPECTED` (planned)

---

## Payment Interaction

Payment resolves the inventory reservation lifecycle.

### Payment Success

On successful payment:

- Inventory reservations are **committed**.
- Physical stock is decremented.
- Order transitions: `CREATED → PAID`.

This operation is idempotent and protected against race conditions.

### Payment Failure

On payment failure:

- Order is cancelled.
- Inventory reservations are released.
- Physical stock is not decremented.

Result:

CREATED → CANCELLED

cancel_reason = PAYMENT_FAILED

Retrying payment is not supported; a new checkout is required.

---

## Time-Based Expiration (TTL)

Orders in `CREATED` state are not valid indefinitely.

If payment is not completed before reservation TTL expires:

- Reservations are expired.
- Order is cancelled automatically by the system.

Expiration rules:

- Applies only to `ACTIVE` reservations.
- Applies only if the order is still `CREATED`.
- Paid orders are never expired.

Result:

CREATED → CANCELLED

cancel_reason = PAYMENT_EXPIRED

Expiration is executed by a background runner (later via django-q2),
and can be triggered manually via a management command for testing.

---

## Cancellation Paths Summary

| Scenario                  | Order State | Reservation Result | Stock |
| ------------------------- | ----------- | ------------------ | ----- |
| Payment success           | PAID        | COMMITTED          | ↓     |
| Payment failure           | CANCELLED   | RELEASED           | =     |
| TTL expiration            | CANCELLED   | EXPIRED            | =     |
| Customer cancel (CREATED) | CANCELLED   | RELEASED           | =     |
| Out-of-stock on checkout  | —           | —                  | =     |

---

## Architectural Rationale

This lifecycle design ensures that:

- Overselling is prevented without prematurely decrementing stock.
- Inventory logic is explicit, auditable, and WMS-friendly.
- Time-based behavior is deterministic and testable.
- Order states remain minimal; reasons are expressed as metadata.

This separation enables future integrations such as:

- External WMS systems
- Asynchronous fulfillment workflows
- Detailed audit logging and reconciliation

---

## Related Documents

- [ADR-025: Inventory Reservation Model](../decisions/ADR-025-Inventory-Reservation-Model.md)
- [Current Architecture Baseline](Current%20Architecture%20Baseline.md)
- Order Fulfillment Architecture (planned)
