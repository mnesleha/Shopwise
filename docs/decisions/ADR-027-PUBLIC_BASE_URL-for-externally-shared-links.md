# ADR-0XX: PUBLIC_BASE_URL for externally shared links

**Status**: Accepted

**Date**: Sprint 9

**Decision type**: Architecture

## Context

Shopwise needs to generate URLs that are shared outside the backend runtime context (e.g., email links for guest order access, email verification, password reset). These links must be absolute URLs so recipients can open them from any device.

At the time of introducing guest order access, the frontend UI is not implemented yet. However, we still need deterministic URL generation for tests and for future email delivery.

## Decision

Introduce a single configuration setting `PUBLIC_BASE_URL` (string) that represents the public-facing base URL used when generating externally shared links.

For MVP (backend-only), `PUBLIC_BASE_URL` points to the backend host (e.g., `http://127.0.0.1:8000`) and links can target API endpoints directly.

When a frontend is introduced, `PUBLIC_BASE_URL` will be changed to the frontend host (e.g., `https://shopwise.example`) without changing business logic.

## Consequences

- URL generation becomes deterministic and environment-configurable.
- Email delivery (Mailpit/SMTP) can reuse the same URL generator without relying on request context.
- Switching from backend API links to frontend UI links is a configuration change only.
