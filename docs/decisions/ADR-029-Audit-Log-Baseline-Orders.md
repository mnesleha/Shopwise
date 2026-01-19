# ADR-XXX: Audit Log Baseline (Orders)

**Status**: Accepted

**Date**: Sprint 9

**Decision type**: Architecture

## Context

The Shopwise backend requires an auditable record of critical domain events,
primarily around Orders and Inventory, to support:

- operational troubleshooting,
- security and compliance needs,
- future integrations (e.g. WMS, ERP, analytics),
- and business transparency (who did what, when, and why).

At this stage (MVP), the audit log must:

- be lightweight,
- non-blocking (best-effort),
- extensible to other domains,
- and independent of any external logging or SIEM solution.

## Decision

We introduce an **Audit Log MVP** with the following design principles:

### 1. Dedicated Audit Domain App

A separate `auditlog` Django app is used to:

- isolate audit concerns from business logic,
- allow future replacement or extension without refactoring core domains,
- avoid coupling to Django admin logs or third-party libraries.

### 2. Explicit Audit Event Model

Audit events are stored as immutable records with the following core fields:

- `entity_type` – logical domain entity (e.g. "order")
- `entity_id` – identifier of the affected entity
- `action` – normalized audit action (e.g. `order.cancelled`)
- `actor_type` – system, user, admin
- `actor_id` – optional reference (user id)
- `metadata` – JSON payload with contextual details
- `created_at` – event timestamp

Indexes are applied to support:

- lookup by entity,
- time-based queries,
- future reporting use cases.

### 3. Service-Layer Emission (Single Entry Point)

Audit events are emitted **only from service-layer functions**, never directly
from views or serializers.

This ensures:

- consistency across all code paths,
- correct ordering relative to state transitions,
- future compatibility with domain events.

### 4. Best-Effort Semantics (Fail Silently)

Audit logging **must never block** the primary business flow.

If audit persistence fails:

- the exception is caught,
- logged via technical logging (e.g. Python logger / Sentry later),
- the original business operation continues.

This is intentional and explicitly accepted for MVP.

### 5. Explicit Action Registry

Audit actions are defined centrally (e.g. `auditlog.actions`) to:

- avoid string duplication,
- provide discoverability,
- enforce naming consistency.

Actions are not stored as enums in the database to allow:

- easy extension,
- no schema migration when adding new actions.

## Current Scope (Sprint 9)

Audit events are emitted for:

- Order cancellation (customer & system)
- Payment success / failure
- Inventory reservation expiration
- Order fulfillment transitions (ship, deliver)

## Consequences

### Positive

- Clear, centralized audit trail for Orders.
- Safe, non-blocking design.
- Easy extension to other domains (Payments, Promotions, Auth).

### Trade-offs

- No guaranteed delivery (best-effort).
- No UI or admin view yet.
- No retention or cleanup strategy yet.

## Follow-ups / Future Work

- Scheduled cleanup/retention policy.
- Admin read-only audit log view.
- Emission of audit events as domain events (outbox pattern).
- External log sink integration (Sentry, ELK, etc.).
