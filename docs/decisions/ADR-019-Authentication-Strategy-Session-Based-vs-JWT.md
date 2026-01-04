# ADR-019 Authentication Strategy: Session-Based vs JWT (Decision: JWT)

**Status**: Accepted

**Date**: Sprint 8

**Decision type**: Architecure

## Context

Sprint 8 introduces authentication for a React SPA frontend and for API automation via pytest/Postman in CI. We must decide between:

- Django session-based authentication (cookie + CSRF), and
- token-based authentication using JWT (Bearer tokens).

Constraints and goals:

- React-friendly API usage without CSRF friction.
- Postman-friendly automation (local + CI) without relying on cookies.
- High CV value: clear demonstration of stateless API auth and RBAC.
- Maintain consistent error shape and OpenAPI alignment.

## Decision:

We will implement JWT-based authentication for Shopwise.

### JWT approach

- Clients authenticate using `Authorization: Bearer <access_token>`.
- Tokens are issued by login endpoint(s) and used for subsequent requests.
- We will support roles/permissions via user roles (e.g., customer/admin) enforced server-side.

Recommended JWT model (implementation detail, not strictly required by this ADR):

- Short-lived access token
- Optional refresh token for longer sessions
- Standard DRF integration (e.g., SimpleJWT) for maintainability

### Why JWT over session-based auth

- React-friendly: avoids CSRF requirements and common cookie/CORS pitfalls in SPA setups.
- Postman/CI-friendly: simple pre-request scripts and environment variables; no dependency on cookie jars or session state.
- CV value: demonstrates modern API authentication patterns, Bearer auth, and role-based authorization.
- Testability: easier to inject tokens in frontend E2E tests (Cypress/Playwright) than to simulate secure cookies reliably.

## Consequence

- The API becomes stateless from the client perspective (per-request Authorization header).
- We must implement secure token issuance and validation (and document it in OpenAPI).
- We must adjust automated tests:
  - pytest helpers for token creation and authenticated requests,
  - Postman folder-level helpers to acquire and reuse tokens.
- We must define token expiration and handle “expired token” errors consistently with the unified error schema.
- For local development and CI, JWT simplifies E2E flows and reduces infrastructure coupling.
