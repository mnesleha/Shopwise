# ADR-017 Inventory Reservation and Order Status Policy

**Status**: Accepted

**Date**: Sprint 8

**Decision type**: Architecure

## Context

Shopwise currently supports the core flow Cart → Checkout → Order → Payment. In Sprint 8 we want to introduce MVP fulfillment behavior and inventory updates. The project is a fake e-shop intended for CV demonstration, so we explicitly avoid real warehouse/shipping complexity.

We need to decide:

- When product stock is decremented (reservation strategy).
- Which order statuses are part of the MVP, and what they mean.
- How to prevent duplicate side effects (idempotency) when payment events are retried.

## Decision:

### Order status lifecycle (MVP)

We will use the following order status flow:

- `CREATED` → `PAID` → `SHIPPED`

We will NOT use `DELIVERED` in the MVP (it remains out of scope and is not required for the CV scenario).

### Inventory reservation policy

- Stock will be decremented when an order transitions to `PAID`.
- A successful payment is treated as a reservation of inventory.

### Idempotency guarantees

- The `PAID` transition and the stock decrement MUST be idempotent.
- If the payment success event is processed multiple times (retries / duplicated calls), inventory must only be decremented once.

Implementation-level expectations:

- Payment success handling must detect that the order is already in `PAID` (or that inventory has already been decremented) and become a no-op.
- If order items exist, stock decrement is computed from order item quantities.

### Shipping policy (MVP fulfillment)

- `SHIPPED` is a fulfillment status with NO additional pricing or inventory effects.
- Transition to `SHIPPED` is triggered by an admin-only action to demonstrate roles/permissions (CV value).
- We will provide:
  1. a single-order ship action (admin-only), and
  2. an optional bulk ship action (admin-only) for demonstration.

Recommended API shape (non-binding, for consistency):

- `POST /api/v1/admin/orders/{id}/ship` (ship a single PAID order)
- `POST /api/v1/admin/orders/ship` (bulk ship PAID orders by IDs or by filter)

## Consequence

- Inventory correctness is simple and testable: payment success immediately reserves inventory.
- We avoid warehouse complexity while still demonstrating a realistic order lifecycle.
- Admin-only shipping provides clear RBAC/permissions value for the CV and allows showcasing automation/testing of privileged operations.
- Extra implementation work: we must add robust idempotency checks and corresponding tests (pytest + Postman E2E).
- Operationally, `SHIPPED` becomes a “business completion” marker without affecting stock.
