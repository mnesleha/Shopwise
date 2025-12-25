# Test Strategy

## Purpose of This Document

This document describes the **overall testing strategy** for the Shopwise project.

Its purpose is to explain:

- how quality is approached and managed
- which types of tests are used and why
- how testing supports development, documentation, and delivery

The strategy focuses on **risk-driven, workflow-oriented testing** rather than exhaustive coverage.

## Quality Objectives

The primary quality objectives of Shopwise are:

- correctness of core business workflows
- clarity and predictability of API behavior
- early detection of regressions
- high confidence during refactoring
- fast feedback during development

Quality is defined primarily in terms of **behavior**, not implementation.

## Scope of Testing

Testing in Shopwise focuses on:

- Cart, Order, and Payment workflows
- business rules and state transitions
- API contracts and permissions
- error handling and edge cases

Non-functional aspects (e.g. performance) are addressed separately
and introduced incrementally.

## Testing Approach

Shopwise applies a layered testing approach guided by risk and impact.

**Key principles**:

- Test business rules close to where they live  
  Domain invariants are validated using unit tests.

- Test workflows at integration level  
  Critical user flows are validated using API integration tests.

- Avoid redundant tests  
  The same behavior is not tested at multiple layers without a clear reason.

- Prefer fewer, meaningful tests over high coverage numbers  
  Test effectiveness is prioritized over test count.

## Test Types and Responsibilities

### Unit tests

Unit tests focus on:

- domain rules
- model validation
- state invariants

They provide fast feedback and support safe refactoring.

### Api Integration Tests

API integration tests focus on:

- endpoint behavior
- permissions and authentication
- state transitions across requests
- error scenarios

These tests validate system behavior as seen by API consumers.

### End-to-End Tests (Postman)

End-to-end tests focus on:

- realistic user workflows
- interactions across multiple endpoints
- high-risk business scenarios

Postman tests serve both as verification and executable documentation.

## Test Data and Environments

- SQLite is used for automated tests to ensure fast and isolated execution
- MySQL is used in local environments to reflect production-like behavior
- Test data is created explicitly and owned by each test

## Automation and CI

Automated tests are executed:

- locally during development
- automatically in CI pipelines

The CI pipeline acts as a quality gate and prevents merging code
that violates core business rules.

## Relationship Between Testing and Documentation

Testing and documentation are treated as complementary activities.

- Tests validate behavior
- Documentation explains intent
- OpenAPI helps detect gaps between the two

Documentation insights are used to:

- identify missing test cases
- improve coverage of edge scenarios

## Out of Scope

The following are intentionally out of scope for this strategy:

- UI-level testing
- load and stress testing (planned for a later phase)
- security testing beyond basic authentication and authorization

## Summary

The testing strategy in Shopwise emphasizes:

- risk-based prioritization
- workflow-oriented validation
- tight integration with development and documentation

The goal is not maximum coverage,
but maximum confidence in the system's most critical behavior.
