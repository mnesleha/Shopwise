# ADR-024: Tenant-Friendly Guardrails (Non-Blocking White-Label Path)

**Decision type**: Architecture

**Status**: Proposed

**Date**: Sprint 9

**Authors**: Shopwise team

## Context

Shopwise is currently developed as a CV showcase project with a growing business intent (SaaS starter kit / potential white-label). The current target is **single-tenant** (one shop per deployment). However, some architectural choices can unintentionally “lock in” a single-tenant assumption so strongly that a future multi-shop/white-label expansion would require disruptive and expensive refactoring.

We want to avoid premature multi-tenancy engineering while keeping a clear, low-cost expansion path.

## Decision

We adopt tenant-friendly (non-blocking) guardrails across the codebase and documentation. These guardrails do not introduce multi-tenancy now, but ensure we do not block it later.

1. **Explicit “shop configuration” boundary (settings-driven)**

   Branding and shop identity are treated as configuration, not hardcoded logic:

   - shop name, support email, default currency, and email “from” identity must be sourced from settings/environment variables.
   - no hardcoded literals in business logic beyond local defaults.

2) **Public vs Admin API separation**

   Operational/backoffice actions are not exposed via customer-facing endpoints:

   - customer-facing endpoints remain under `/api/v1/...`
   - admin/backoffice endpoints live under `/api/v1/admin/...` and are protected by explicit RBAC/permissions.

   This boundary is kept even in single-tenant mode.

3) **Auditing and background processes are scope-aware**

   When introducing cross-cutting infrastructure (audit logs, scheduled cleanup jobs, email workflows), we include a **nullable scope/context field** to avoid future schema rewrites:

   - audit events include `context` (JSON) or `scope_key` (nullable)
   - scheduled cleanup jobs operate on well-defined filters that can later be scoped
   - initial implementation may use a default/NULL scope.

4) Seed/test data are namespace-friendly

   Deterministic seed profiles and E2E fixtures must avoid assumptions that prevent later scoping:

   - stable “keys” or “names” are preferred over raw numeric IDs
   - seed data supports referencing entities by key/name
   - avoid global uniqueness assumptions that would break when “two shops” exist in one database (unless explicitly intended).

5) **No multi-tenant runtime behavior in pre-1.0**

   This ADR does not introduce:

   - a `Shop/Tenant` database model
   - `shop_id` foreign keys across entities
   - tenant middleware
   - tenant-specific RBAC
   - per-tenant data partitioning

   Multi-tenancy remains a future enhancement and must be introduced via a dedicated ADR when needed.

## Consequences

**Positive**

- Keeps the current system simple (single-tenant) while preserving an upgrade path.
- Improves modularity and clarity (public vs admin boundary).
- Reduces future refactor cost if white-label/multi-shop becomes a requirement.
- Strengthens CV value by showing pragmatic architecture governance.

**Negative / Trade-offs**

- Slight additional discipline in development (settings usage, keeping boundaries clean).
- Some fields (e.g., audit context) exist before they are fully utilized.

## Implementation Notes (Guardrails Checklist)

During PR review and sprint work:

- No hardcoded shop identity/branding in business logic.
- Any “admin action” endpoint must go under `/api/v1/admin/...` with explicit permissions.
- Audit/event records include a scope/context placeholder.
- Seeds/tests reference entities by stable keys/names (not raw IDs).
- If a change requires introducing real multi-tenancy behavior, create a new ADR.

## Related Decisions

[ADR-016](./ADR-016-Postman-CLI-for-API-Contract-and-E2E-Testing-in-CI.md) Postman CLI for API Contract and E2E Testing in CI

[ADR-021](./ADR-021-Pre-1.0-Migration-Reset-Policy.md) Pre-1.0 Migration Reset Policy

[ADR-020](./ADR-020-Custom-User-Model-with-Email-Based-Authentication.md) Custom User Model with Email-Based Authentication
