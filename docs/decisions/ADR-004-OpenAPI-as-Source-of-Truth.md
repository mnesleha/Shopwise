# ADR-004: Introduce OpenAPI as Source of Truth for API Behavior

**Status**: Accepted

**Date**: Sprint 5–6

## Context

The project reached a stage where:

- The API was used in Postman, pytests, and documentation
- Endpoint behavior differed between implementation and expectation
- It was unclear whether the contract was driven by code or documentation

## Decision

OpenAPI (drf-spectacular) is defined as the behavioral contract of the API, not just the documentation.

- OpenAPI describes:
  - status codes
  - response structure (including errors)
  - business meaning of errors
- Tests (Postman + pytest) follow OpenAPI, not the other way around
- If behavior changes, it must be explicitly decided whether:
  - we change the contract
  - or fix the implementation

## Consequences

**Positive**

- Unambiguous reference point for backend, QA and future frontend
- Enabled systematic TDD process (RED → GREEN → REFACTOR)
- Made missing/inconsistent behavior visible (401 vs 403, 400 vs 409)

**Negative**

- Postman is not good at synchronizing OpenAPI changes (manual discipline required)
- Higher demands on documentation consistency
