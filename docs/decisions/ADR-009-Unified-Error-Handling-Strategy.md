# ADR-009: Unified Error Handling Strategy (Cart Domain)

**Status**: Accepted (Cart domain only)

**Date**: Sprint 7

**Decision type**: Architecure

## Context

Original state:

- DRF default errors (`__all__`, lists, dicts)
- inconsistent structures across endpoints
- Postman tests hard to read
- frontend should not have a stable API

## Decision

Standardized error structure introduced:

```json
{
  "code": "CART_EMPTY",
  "message": "Cart is empty"
}
```

Principles:

- Each business error = its own exception
- Exceptions inherit from `APIException`
- Status code is part of exception
- Handler maps exception → unified response
- For validation, possibility of extension with `errors` field (in the future)

Scope:

- Only Cart + Checkout + Cart Items
- Other domains unchanged for now

## Consequences

**Positive**

- Readable, stable API
- Tests verify business meaning, not DRF internals
- Frontend ready

**Negative**

- Refactoring is invasive
- Requires consistency when writing new code
- Not yet applied globally
