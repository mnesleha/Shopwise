# ADR-016 Postman CLI for API Contract and E2E Testing in CI

**Status**: Accepted

**Date**: Sprint 7

**Decision type**: Process

## Context

The project requires automated verification of API behavior in a production-like environment.
Unit and integration tests cover internal logic, but do not validate full request/response flows,
authentication, or API contract behavior from a consumer perspective.

The goal is to:

- validate real API workflows
- run against a real database
- fail fast when API behavior breaks
- keep tests understandable by testers and project managers

## Decision:

Postman API tests are executed in CI using Postman CLI, running cloud-hosted collections and environments against a locally started backend.

The CI pipeline is responsible for preparing the full execution environment, including:

- provisioning a clean MySQL database
- running migrations
- seeding required test data
- starting the backend server
- verifying backend health

Postman CLI:

- does not start the backend
- does not prepare data
- executes only API-level tests and assertions

## Consequence

**Positive**:

- Full end-to-end API flows are validated automatically
- Tests run against a real database (MySQL)
- Clear separation of responsibilities between CI and Postman
- Failures point to real API or data issues
- Test results are accessible to non-developers

**Negative / Trade-offs**:

- Requires explicit and reliable data seeding
- CI pipeline becomes more complex
- Postman Cloud becomes a required external dependency

**Notes**:

- Collections and environments are referenced by Postman Cloud IDs, not committed JSON files.
- JUnit reports are generated for CI visibility.
