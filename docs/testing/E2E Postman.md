# End-to-End Testing with Postman

## Purpose of This Document

This document describes the role of **Postman-based end-to-end (E2E) testing**
in the Shopwise project.

Its purpose is to explain:

- why Postman is used alongside automated tests
- which scenarios are covered at E2E level
- how Postman tests complement pytest-based testing

## Why Postman

Postman is used in Shopwise as a lightweight and flexible tool for:

- validating complete user workflows
- performing manual and semi-automated E2E verification
- serving as executable API documentation
- quickly reproducing and debugging issues

Postman is inentionally not used as the primary automation framework, but as a complementary E2E layer.

## Role of E2E Tests

End-to-end tests focus on validating that the system behaves correctly
from an API consumer perspective.

They verify:

- correct interaction between multiple endpoints
- realistic request sequencing
- correct state transitions across the system

E2E tests answer the question:
"Does the system work as expected when used in a realistic way?"

## Covered E2E Scenarios

The Postman collection includes E2E scenarios such as:

- retrieve or create active cart
- add valid items to cart
- reject invalid cart operations
- checkout cart
- verify order creation
- simulate successful payment
- verify order status after payment

These scenarios represent the **highest-risk business workflows** in the system.

## Relationship to Automated Tests

Postman E2E tests do not replace automated pytest tests.

Instead:

- pytest tests validate logic and workflows automatically
- Postman tests validate realism and usability

The same behavior is not intentionally tested twice unless:

- the scenario is business critical
- manual verification provides additional confidence

## Test Data and State Management

Postman tests:

- create their own test data
- store intermediate values using variables
- cleanly follow the intended workflow sequence

Tests do not rely on pre-existing database state.

This ensures repeatibility and reduces false positives.

## Postman as Executable Documentation

The Postman collection is treated as executable documentation.

It allows team members to:

- explore API behavior interactively
- understand request and response structures
- validate assumptions without reading code

This is particularly useful for onboarding and cross-role communication.

## Limitations and Non-Goals

Postman E2E tests are intentionally not used for:

- load or performance testing
- high-volume automation
- UI-level testing

These concerns are addressed using other tools and approaches.

## Relationship to OpenAPI

OpenAPI documentation and Postman complement each other:

- OpenAPI defines the API surface and contracts
- Postman validates real-world usage of those contracts

OpenAPI specifications can be imported into Postman
to bootstrap collections and reduce duplication.

## Summary

In Shopwise, Postman-based E2E testing is used to:

- validate critical workflows end-to-end
- support manual exploration and debugging
- act as executable API documentation

It complements automated testing by focusing on realism,
usability, and confidence in system behavior.
