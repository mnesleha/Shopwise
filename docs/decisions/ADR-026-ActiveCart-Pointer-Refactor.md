# ADR-026: ActiveCart Pointer Refactor (Decouple "active cart" from Cart rows)

**Status**: Accepted

**Date**: Sprint 9

**Decision type**: Architecture

**Scope**: carts domain, cart resolver/merge/claim, cart API behavior, concurrency safety

## Context

Historically, the system modeled the "active cart" for a user by querying the `Cart` table directly (e.g., `Cart.objects.get_or_create(user=user, status=ACTIVE)`), with additional logic attempting to enforce “only one active cart per user”.

During implementation of new Cart Items endpoints:

- `PUT /api/v1/cart/items/{product_id}/` (canonical)
- `DELETE /api/v1/cart/items/{product_id}/`
- legacy `POST /api/v1/cart/items/` (UPSERT alias)

we introduced concurrency/race-condition tests (MySQL) and encountered real production-like races:

- Multiple concurrent requests created multiple `ACTIVE` carts for the same user (`MultipleObjectsReturned`).
- Attempts to enforce uniqueness using a conditional unique constraint (or computed flags) were not portable:
  - MySQL does not support partial/conditional unique constraints.
  - “computed active” flags become cross-cutting and fragile across all flows (merge/convert/claim).

We need a DB-backed, cross-database invariant guaranteeing exactly one “active cart reference” per user without relying on conditional constraints or hacks in the `Cart` row.

## Decision

Introduce a dedicated **ActiveCart pointer** concept as a separate persistence structure:

- A new table/model (e.g., `ActiveCart`) that stores a **single pointer** to the current active cart per user.
- All code paths that need an active cart must go through the **ActiveCart service** (single entrypoint).

This decouples:

- cart lifecycle history (multiple `Cart` rows over time, statuses like ACTIVE/CONVERTED/MERGED),
  from:
- the single “currently active cart” reference (one row per user).

## High-level Design

### Data model

- `Cart` remains the canonical cart history entity:

  - May have many rows per user over time.
  - Status changes reflect lifecycle (ACTIVE/CONVERTED/MERGED).
  - Merges keep provenance (`merged_into_cart`, `merged_at`).

- `ActiveCart` (new):
  - `user` (unique)
  - `cart` FK to `Cart`
  - timestamps for auditing/debugging (created_at/updated_at)
  - (Future-ready) place to add tenant_id later ([ADR-024](./ADR-024-Tenant-Friendly-Guardrails.md) guardrails: “tenant-ready, not multi-tenant yet”)

### Service entrypoint

All “get active cart” operations must use `ActiveCartService` (or equivalent):

- `get_or_create_user_active_cart(user) -> Cart`
- `rotate_active_cart(user, new_cart, reason=...)`
- `get_user_active_cart(user) -> Optional[Cart]`

### Resolver changes (cart flows)

- Authenticated request:

  - Resolve active cart via `ActiveCart` pointer.
  - If missing, create a new cart row and bind pointer.
  - No direct `Cart.objects.get_or_create(user=user, status=ACTIVE)` in request paths.

- Anonymous request:

  - Resolve cart via token (cookie/header), as before.
  - ActiveCart pointer is NOT used for anonymous carts.

- Login / claim / merge:
  - After successful merge/claim, **pointer is updated** to the correct cart (the merged target).
  - Old carts remain as historical rows with appropriate status (e.g., MERGED) and provenance fields.

## Consequences

### Positive

- Cross-DB invariant: **exactly one active cart reference per user** (enforced by unique constraint on `ActiveCart.user`).
- Eliminates `MultipleObjectsReturned` failures under concurrency.
- Simplifies reasoning: active cart is a pointer, not “a Cart row with a magic status”.
- Future-ready integration point:
  - WMS/warehouse integration may need stable cart identity boundaries.
  - Audit logging can hook into pointer rotation events.
  - Tenant-ready extension point (store tenant_id later in ActiveCart).

### Trade-offs

- Requires migration + updates across all code paths that previously assumed status-based uniqueness.
- Tests that asserted “only one Cart row with status ACTIVE” must be adjusted:
  - “only one ActiveCart per user” is now the invariant.
  - Multiple Cart rows may exist historically.

## Current Behavior (as implemented)

- GET `/api/v1/cart/`:

  - Auth user: returns cart resolved through ActiveCart pointer (stable across requests).
  - Guest: returns cart resolved by token; sets cookie when new cart is created.

- PUT `/api/v1/cart/items/{product_id}/`:

  - Race-safe UPSERT using (cart, product) unique constraint on CartItem + retry loop for DELETE-vs-PUT race.
  - Returns cart snapshot.

- DELETE `/api/v1/cart/items/{product_id}/`:

  - Removes item and returns cart snapshot.

- POST `/api/v1/cart/items/` (legacy alias):
  - Behaves as UPSERT (set quantity).
  - Returns item snapshot for backwards compatibility.

## Notes / Follow-ups

- Emit a domain event (future): `active_cart_rotated` from the service entrypoint.
- Add optional “reason” metadata on pointer rotation (defer to audit logs).
- Ensure seed scripts and test helpers use the service entrypoint rather than creating status-based carts directly.
