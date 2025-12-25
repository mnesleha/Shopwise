# Coverage vs. Risk

## Purpose of This Document

This document explains **how test coverage in Shopwise is driven by risk**, not by the goal of achieving high coverage numbers.

Its purpose is to clarify:

- why certain areas are tested more extensively than others
- how testing effort is prioritized
- how risk influences test design and scope

## Risk-Driven Testing Philosophy

In Shopwise, testing is guided by the principle that:
not all parts of the system carry the same level of risk.

Risk is evaluated based on:

- business impact
- likelihood of failure
- complexity of logic
- cost of defects

## High-Risk Areas

The following areas are considered high risk and receive the highest testing attention.

### Cart and Checkout Workflow

- Central business workflow
- Multiple state transitions
- Strong dependency on correct validation
- Direct impact on order creation

Failure in this area would break the core functionality of the system.

### Order State Transitions

- Immutable business results
- Payment-driven state changes
- Security-sensitive (user ownership)

Errors here could lead to incorrect financial or transactional outcomes.

### Payment Processing (Fake Payment API)

- Explicit state transitions
- Failure and retry scenarios
- One-to-one relationship with Order

Payment logic is tested to ensure deterministic and predictable behavior.

## Medium-Risk Areas

The following areas carry moderate risk and are tested accordingly.

### Product and Category Management

- Relatively stable data
- Limited state changes
- Mostly CRUD-style behavior

These areas are tested for correctness but do not require exhaustive wokflow testing.

### API Permissions and Access Control

- User-scoped data access
- Authentication and authorization rules

Permissions are tested to ensure proper isolation between users.

## Low-Risk Areas

The following areas are considered low risk:

- Static reference data
- Read-only endpoints
- Simple lookup operations

Testing focuses on basic correctness rather then exhaustive scenarios.

## Coverage Decisions

Coverage decisions in Shopwise follow these guidelines:

- High-risk areas:

  - deep workflow coverage
  - multiple negative and edge-case scenarios
  - E2E validation

- Medium-risk areas:

  - representative test coverage
  - key validation and permission checks

- Low-risk areas:

  - minimal, targeted tests

  Coverage is considered sufficient when risk is adequately mitigated.

## Coverage Metrics

Code coverage metrics are treated as **informational**, not as a primary success criterion.

- Coverage numbers are used to:

  - identify completely untested areas
  - support refactoring decisions

- Coverage numbers are not used to:
  - define quality targets
  - compare test effectiveness

## Relationship to Test Pyramid

Risk directly influences the shape of the test pyramid:

- high-risk workflows drive API and E2E tests
- stable logic is covered primarily by unit tests
- low-risk areas receive minimal coverage

## Summary

In Shopwise, test coverage is intentionally uneven.

This unevenness reflects:

- business priorities
- risk concentration
- pragmatic testing decisions

The goal is not maximal coverage,
but maximal confidence where it matters most.
