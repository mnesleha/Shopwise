# ADR-020: Custom User Model with Email-Based Authentication

**Status**: Accepted

**Date**: Sprint 8

**Decision type**: Architecure

## Context

Shopwise is evolving from a pure CV showcase into a reusable backend foundation with explicit business intent:

- SaaS starter kit
- White-label solution
- Freelance delivery for e-commerce backends

In such contexts, user identity becomes a core architectural concern rather than an implementation detail.

The default Django `auth.User` model does not enforce email uniqueness and treats `username` as the primary identifier. This design conflicts with common e-commerce and SaaS requirements, including:

- Email-based authentication
- Guaranteed uniqueness of user email addresses
- Future email workflows (order notifications, password reset, verification)
- Clean and extensible identity model suitable for long-term evolution

Previous attempts to enforce email uniqueness at the database level without a custom user model resulted in database-specific workarounds that reduce clarity and maintainability.

Given the early stage of the project (pre-1.0), now is the optimal time to introduce a custom user model before additional domain complexity and external dependencies accumulate.

## Decision

We will introduce a **custom user model** based on `AbstractUser` and configure the application to use email-based authentication.

**Key decisions**:

- A new Django app (`accounts`) will define the custom user model.
- The custom user model will inherit from `AbstractUser` to preserve Django’s built-in permissions and admin integration.
- `email` will be:
  - required for authentication,
  - unique at the database level,
  - normalized (lowercased) at input boundaries.
- Email will be the primary login identifier (`USERNAME_FIELD = "email"`).
- `AUTH_USER_MODEL` will be set to `accounts.User`.
- All foreign key references to `User` across the domain (carts, orders, payments, etc.) will reference `settings.AUTH_USER_MODEL`.
- `username` is retained for Django compatibility only; it is not used for authentication nor exposed as a primary identity field. The UI display name is derived from `first_name` + `last_name`, with a fallback to email.

## Consequences

**Positive**

- Clean and explicit identity model aligned with modern SaaS and e-commerce practices.
- Native database enforcement of email uniqueness (no DB-specific hacks).
- Clear foundation for future features:
  - email verification
  - password reset flows
  - order and shipment notifications
  - role and permission extensions
- Increased architectural credibility for use as a starter kit or white-label solution.
- Reduced long-term migration risk (avoids costly late-stage switch to a custom user model).

**Negative / Costs**

- Requires coordinated refactoring across authentication, domain models, tests, seed data, and Postman collections.
- Introduces a breaking change in user identity handling.
- Requires a database schema reset during development (handled explicitly by [ADR-021](ADR-021-Pre-1.0-Migration-Reset-Policymd)).

**Risk Mitigation**

- The change is performed pre-1.0 under an explicit migration policy (see [ADR-021](ADR-021-Pre-1.0-Migration-Reset-Policymd)).
- All changes are implemented test-first (pytest and Postman).
- Scope is intentionally limited to identity and authentication concerns only.
