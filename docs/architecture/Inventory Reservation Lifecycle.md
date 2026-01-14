# Inventory Reservation TTL Lifecycle

## Purpose

Shopwise separates **holding stock** (reservation) from **physical stock decrement** (commit) to prevent overselling and to stay WMS-friendly. `Product.stock_quantity` represents **physical stock**. Availability for reservation is computed as:

`available = stock_quantity - sum(ACTIVE reservations for product)`

This policy is defined in ADR-025.

## Where TTL is applied

TTL is applied at **checkout time** when ACTIVE reservations are created. Each reservation stores an explicit `expires_at` timestamp.

TTL values are configurable via environment variables:

- `RESERVATION_TTL_GUEST_SECONDS` (default 900 = 15 min)
- `RESERVATION_TTL_AUTH_SECONDS` (default 7200 = 2 h)

## Expiration runner (background job / management command)

Reservation expiration is handled by a scheduled runner (later: django-q2 job). The runner:

- finds reservations with `status=ACTIVE` and `expires_at < as_of_time`
- applies only if the associated order is still `CREATED`
- transitions reservations to terminal state `EXPIRED` (treated as release with reason `PAYMENT_EXPIRED`)
- cancels the order with cancellation metadata (`cancel_reason=PAYMENT_EXPIRED`, `cancelled_by=SYSTEM`)

Paid orders are not affected: after payment success, reservations are `COMMITTED` and the order becomes `PAID`.

## Sequence diagram

```mermaid
sequenceDiagram
  actor Customer
  participant API as API
  participant SVC as InventoryReservationService
  participant DB as Database

  Customer->>API: POST /cart/checkout
  API->>SVC: reserve_for_checkout(order, items)
  SVC->>DB: INSERT InventoryReservation(status=ACTIVE, expires_at=now+TTL)
  API-->>Customer: 201 Order(status=CREATED)

  alt Payment success
    Customer->>API: POST /payments {result: success}
    API->>SVC: commit_reservations_for_paid(order)
    SVC->>DB: UPDATE reservations ACTIVE->COMMITTED (committed_at)
    SVC->>DB: UPDATE product.stock_quantity -= qty
    SVC->>DB: UPDATE order CREATED->PAID
    API-->>Customer: 201 Payment(SUCCESS)
  else No payment / TTL passes
    Note over SVC,DB: scheduled runner / management command
    SVC->>SVC: expire_overdue_reservations(as_of)
    SVC->>DB: UPDATE reservations ACTIVE->EXPIRED (release_reason=PAYMENT_EXPIRED)
    SVC->>DB: UPDATE order CREATED->CANCELLED (PAYMENT_EXPIRED)
  end
```

## Operational Notes

- The expiration runner uses `as_of` as a cutoff time: a reservation is overdue if `expires_at < as_of`.

`--dry-run` (CLI) is a read-only estimate and intentionally avoids locks to minimize operational impact.
