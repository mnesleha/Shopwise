# Cart–Order Lifecycle

## Purpose of This Document

This document describes the **lifecycle and workflow transitions** between Cart and Order
in the Shopwise system.

Its goal is to explain:

- how user intent evolves into a finalized order
- which states exist and why
- where business rules are enforced
- how the lifecycle is validated through tests

This document focuses on **process flow and state transitions**, not implementation details.

## Conceptual Overview

In Shopwise, the purchasing process is intentionally split into two distinct phases:

1. **Intent phase** – represented by Cart
2. **Result phase** – represented by Order

This separation ensures clarity between:

- what the user _plans_ to buy
- what the system has _committed_ to as a transaction

## Cart Lifecycle

Cart represents a mutable container of user intent.

A cart can exist in one of the following states:

- ACTIVE
- CONVERTED

### ACTIVE

An ACTIVE cart:

- is automatically created when requested by the user
- can be freely modified (add / remove items, change quantities)
- enforces validation rules on cart items
- is the only cart state eligible for checkout

A user can have at most one ACTIVE cart at any time.

### CONVERTED

A CONVERTED cart:

- represents a cart that has been successfully checked out
- is no longer modifiable
- exists only for historical and traceability purposes

Once a cart is CONVERTED, it cannot transition back to ACTIVE.

## Checkout Process

Checkout is the **only operation** that converts a Cart into an Order.

Checkout:

- validates cart contents
- creates an Order as a snapshot of cart state
- transitions cart state from ACTIVE to CONVERTED
- creates a new empty ACTIVE cart for the user

Checkout is allowed only if:

- the cart is ACTIVE
- the cart contains at least one item
- all cart items pass validation rules

If these conditions are not met, checkout fails with a client error.

## Order Lifecycle

Order represents the result of a completed checkout.

Orders are created in a controlled and explicit manner and are not user-modifiable.

Orders can exist in the following states:

- CREATED
- PAID
- PAYMENT_FAILED

### CREATED

CREATED is the initial state of an Order.

An order in this state:

- has been created from a cart
- contains a snapshot of items and prices
- awaits payment outcome

### PAID

PAID indicates that payment for the order was successful.

In this state:

- the order is considered finalized
- no further state transitions related to payment are expected

### PAYMENT_FAILED

PAYMENT_FAILED indicates that a payment attempt was made but did not succeed.

In this state:

- the order remains immutable
- payment may be retried depending on future extensions
- no cart rollback occurs

## Payment Interaction

Payment is an explicit action performed after checkout.

Key characteristics:

- one-to-one relationship between Order and Payment
- payment outcome drives order state transition
- payment does not modify order contents

Payment is intentionally modeled as a separate step to:

- reflect real-world workflows
- simplify testing and reasoning

## State Transition Summary

Cart:

ACTIVE → CONVERTED

Order:

CREATED → PAID

CREATED → PAYMENT_FAILED

No ther transitions are allowed.

## Error Scenarios and Safeguards

The lifecycle enforces several safeguards:

- checkout of empty cart is rejected
- checkout of non-ACTIVE cart is rejected
- order cannot be created directly via API
- duplicate payments are rejected
- unauthorized access to orders is blocked

These safeguards are enforced through:

- application-level validation
- API permissions
- automated tests

## Validation Through Testing

The Cart–Order lifecycle is validated through multiple layers of tests:

- unit tests:

  - cart invariants
  - item validation rules

- API integration tests:

  - checkout behavior
  - state transitions
  - permission enforcement

- E2E tests (Postman):
  - full user workflow from cart creation to payment

The lifecycle is considered stable only if all test layers are green.

## Summary

The Cart–Order lifecycle is a central design element of Shopwise.

By explicitly separating intent from result and enforcing strict state transitions,
the system achieves:

- clarity of responsibility
- realistic workflow modeling
- improved testability
- stronger guarantees around data integrity
