# ADR-018 Anonymous Cart and Cart Merge on Login

**Status**: Accepted

**Date**: Sprint 8

**Decision type**: Architecure

## Context

Shopwise needs an anonymous shopping experience (guest users) before authentication is implemented. In Sprint 8 we introduce:

- Anonymous carts (session/token-based identification).
- A deterministic merge/adoption policy when the user logs in.
- Clear invalidation of the anonymous cart to avoid cart leakage or repeated merges.

We must define:

- How the anonymous cart is identified.
- How it is converted into a user cart or merged.
- How to handle stock conflicts during merge.
- How to invalidate/deactivate the anonymous cart after merge/adoption.
- Idempotency rules for repeated login attempts.

## Decision:

### Anonymous cart identification

- An anonymous cart is identified by an opaque cart token (guest token) provided by the client.
- The token is treated as a bearer secret (not guessable).
- The server may store a hash of the token (recommended) rather than the raw token.

### Merge/adoption policy on login (silent merge)

On login, if an anonymous cart exists:

1. If the user has NO active cart:

- Adopt the anonymous cart:
  - Assign the cart to the authenticated user.
  - Clear/remove the anonymous token.
  - Keep the cart active as the user cart.

2. If the user HAS an active cart:

- Merge items from the anonymous cart into the user cart:
  - For each product: sum quantities (`qty_user + qty_anon`).
  - If the resulting quantity exceeds available stock:
    - MVP behavior: return `409 CONFLICT` with a domain error code (e.g., `INSUFFICIENT_STOCK_FOR_MERGE`)
    - No partial merge: operation is atomic (all-or-nothing).
  - If merge succeeds, the anonymous cart is invalidated/deactivated.

This merge is silent (no “choose merge vs replace” UX). The goal is deterministic behavior and stable E2E automation.

### Invalidate / delete process for anonymous cart

After adoption or successful merge:

- The anonymous token MUST be invalidated so it cannot be reused.
- The anonymous cart MUST NOT remain usable as an anonymous cart.

Recommended approach (soft-close, audit-friendly):

- Clear the anonymous token (or its hash).
- Mark the cart as inactive OR set a terminal state such as `MERGED` / `CLOSED`.
- (Optional) Record linkage: store `merged_into_cart_id` if a separate cart was the merge target.

Hard-delete is not required and is discouraged if we want debugging/audit value.

### Idempotency

- Merge/adoption must be idempotent:
  - If the anonymous cart token has already been adopted/merged and token invalidated, repeating login does nothing (no duplicate items).
  - The server behavior is deterministic even with repeated requests.

## Consequence

- Guest-to-user transition is deterministic and easy to automate in Postman/CI:
  - Guest adds items → login → cart becomes the user cart or merges into it.
- Risk of cart leakage is reduced by token invalidation and deactivation.
- We introduce a clear domain conflict case (409) for stock overflow during merge, which is testable and explicit.
- Additional implementation complexity:
  - atomic merge logic,
  - stock checks during merge,
  - cart lifecycle fields (token + closed status),
  - comprehensive tests for idempotency and conflict behavior.
