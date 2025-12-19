# Test Pyramid – Shopwise

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

Unit tests form the largest part of the test suite.

## Integration Tests

Purpose:

- Verify interaction between components

Scope:

- REST API endpoints
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

## Risks and Mitigation

Risk:

- Too many E2E tests slowing pipeline

Mitigation:

- Strict control over E2E scope
- Prefer integration tests where possible

## Summary

The test pyramid ensures:

- Fast feedback
- High confidence
- Sustainable test maintenance
