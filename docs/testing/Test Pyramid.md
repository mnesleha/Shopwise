# Test Pyramid

This document describes the test pyramid adopted in the Shopwise project.
It defines different test levels, their purpose, tools, and relative proportions.

## Test Pyramid Overview

The Shopwise project follows the classic test pyramid approach:

          E2E Tests
       Integration Tests
    Unit Tests

The goal is to maximize confidence while keeping feedback fast
and maintenance cost low.

## Unit Tests

Unit tests form the base of the test pyramid.

They focus on:

- domain rules
- model validation
- state invariants

Characteristics:

- fast execution
- high isolation
- precise failure localization

Unit tests use an in-memory SQLite database
to minimize execution time and external dependencies.

Purpose:

- Verify individual units of logic in isolation

Scope:

- Business logic
- Services
- Model methods
- Utility functions

Tools:

- pytest (backend)
- Vitest (frontend)

Unit tests form the largest part of the test suite. They provide immediate feedback during development and support safe reafactoring.

## Integration API Tests

API integration test form the **most important layer** of the Shopwise test pyramid.

Integration tests are executed against a MySQL database
to reflect production-like behavior.

Purpose:

- Verify interaction between components

Scope:

- Business workflows
- Interaction between multiple components
- REST API endpoints
- State transitions across requests
- Database integration
- Authentication and authorization

Tools:

- pytest
- Django test client
- test database (MySQL)

## End-to-End Tests

Purpose:

- Validate complete user flows from UI to database

Scope:

- User registration and login
- Browsing products
- Placing orders
- Mocked payment flow

Tools:

- Postman
- Playwright

## Test Distribution (Proposal)

- Unit tests: ~70%
- Integration tests: ~20%
- E2E tests: ~10%

Exact proportions may evolve as the project grows.

## Out of Scope Testing

- UI visual regression
- Cross-browser testing
- Security testing

## Test Data Management

- Test data is created programmatically
- Factories are used for backend tests
- No shared mutable test data

## CI/CD Execution Strategy

- Unit tests run on every push
- Integration tests run on every pull request
- E2E tests run on main branch and before deployment

## Relationship to Other Testing Documents

- [Test Strategy](Test%20Strategy.md)  
  Explains _why_ this pyramid exists.

- [Coverage vs Risk](Coverage%20vs%20Risk.md)  
  Explains _where_ test effort is concentrated.

- [E2E Postman](E2E%20Postman.md)  
  Documents _how_ top-level scenarios are validated.

## Summary

The test pyramid ensures:

- Fast feedback
- High confidence
- Sustainable test maintenance
