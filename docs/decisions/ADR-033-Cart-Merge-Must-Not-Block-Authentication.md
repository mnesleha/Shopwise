# ADR-033: Cart Merge Must Be Best-Effort and Must Not Block Authentication

**Status**: Proposed

**Date**: Sprint 11

**Decision type**: Architecture

## Context

The system supports guest carts and authenticated user carts.
When a guest user logs in, the backend performs a guest→user cart merge as a side effect of the login operation.

Current behavior:

- Login triggers cart merge.
- If a stock conflict occurs during merge, the login endpoint returns 409 CART_MERGE_STOCK_CONFLICT.
- Authentication tokens are not issued.
- The user remains unauthenticated.
- Guest cart cookie remains intact.

This behavior tightly couples authentication with cart business logic and results in login failures due to non-authentication concerns.

This is a violation of separation of concerns and leads to poor user experience.

Authentication must not fail due to cart merge conflicts.

## Decision

### 1. Login Must Not Be Blocked by Cart Merge

Authentication (credential validation and token issuance) must be independent of cart merge success.

If credentials are valid:

- The login endpoint MUST return `200 OK`.
- Authentication tokens MUST be issued.
- Guest cart merge MUST be executed in best-effort mode.

No cart merge conflict may prevent login.

### 2. Cart Merge Must Be Best-Effort

During guest→user cart merge:

- Items with identical products must be merged by summing quantities.
- If merged quantity exceeds available stock:
  - Quantity MUST be capped to available stock.
  - A merge warning MUST be recorded.
- Items with zero available stock MAY be removed or capped to zero (implementation-defined, but deterministic).
- Merge MUST never raise a blocking exception for stock conflict.

### 3. Discount Strategy During Merge

When both guest and authenticated carts contain discount codes:

- All candidate discounts must be validated against:
  - Current user
  - Cart contents
  - Expiration
- Only valid discounts are considered.
- The discount producing the lowest total price MUST be applied.
- Tie-breaker rule must be deterministic:
  - Prefer user cart discount over guest cart discount.
  - If still equal, use a deterministic priority rule (e.g., fixed > percentage).
- Expired discounts MUST NOT be applied.

### 4. Login Response Must Include Structured Cart Merge Report

The login response must include a `cart_merge` object describing:

- Whether merge was performed
- Whether cart was adopted or merged
- Stock adjustments
- Skipped items
- Discount decision
  = Any warnings

Example:

```json
{
  "access": "...",
  "refresh": "...",
  "cart_merge": {
    "performed": true,
    "warnings": [
      {
        "code": "STOCK_ADJUSTED",
        "product_id": 125,
        "requested": 3,
        "applied": 1
      }
    ],
    "discount_decision": {
      "chosen": "WELCOME10",
      "rejected": [
        {
          "code": "OLDPROMO",
          "reason": "EXPIRED"
        }
      ]
    }
  }
}
```

If no guest cart existed:

```json
{
  "access": "...",
  "refresh": "...",
  "cart_merge": {
    "performed": false
  }
}
```

Frontend must not rely on cookie heuristics to determine merge outcome.

## Consequences

**Positive**

- Authentication is robust and isolated from cart business rules.
- Improved user experience.
- Deterministic merge behavior.
- Full observability of merge decisions.
- Simplified frontend logic.
- Improved testability (merge can be validated via login response).

**Negative**

- Login response contract becomes richer.
- Merge logic becomes more complex (especially discount evaluation).
- Requires additional unit and integration tests.

## Alternatives Considered

A) Block login on merge conflict (Rejected)

Rejected because authentication must not fail due to cart business rules.

B) Separate merge endpoint called after login

Possible alternative.
Rejected for now to preserve simplicity and maintain merge as login side-effect.

May be reconsidered if login flow complexity increases.

## Guard Rules for Future Development

- Authentication logic must not depend on cart, discount, or inventory domain failures.
- Side effects during login must be best-effort and non-blocking.
- All merge decisions must be deterministic and testable.
- Any merge-related state must be explicitly reported in API responses.
