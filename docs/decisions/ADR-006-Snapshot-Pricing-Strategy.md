# ADR-006: Snapshot Pricing Strategy (price_at_add_time)

**Status**: Accepted

**Date**: Sprint 6

## Context

Major issues with:

- rounding
- product price change between add-to-cart and checkout
- inconsistent calculations between cart, order and serializer

## Decision

Snapshot pricing strategy implemented:

- CartItem.price_at_add_time
  - saved at add-to-cart
  - never recalculated
- Checkout uses snapshot only
- Pricing helper:
  - works with exact values
  - rounds only at the end
- No "back-division" of rounded prices

## Consequences

**Positive**

- Elimination of double-rounding bugs
- Deterministic behavior at checkout
- Correct behavior when changing product price

**Negative**

- Higher discipline requirements (don't touch snapshot)
- Pricing helper is a sensitive piece logic (requires tests)
