# ADR-021: Pre-1.0 Migration Reset Policy

**Status**: Accepted

**Date**: Sprint 8

**Decision type**: Architecure

## Context

Shopwise is currently in an early, pre-1.0 development phase. During this phase, the project is still converging on:

- core domain boundaries,
- identity and authentication strategy,
- database schema stability.

Some architectural decisions (e.g. identity model, inventory semantics) are foundational and difficult to change incrementally once the system matures.

The project has already experienced schema-level changes that required migration resets (e.g. category hierarchy simplification). Continuing to apply incremental migrations for unstable core concepts increases complexity and risk without providing meaningful value at this stage.

At the same time, Shopwise aims to be production-grade and reusable after reaching version 1.0, at which point schema stability and forward-only migrations become mandatory.

## Decision

We explicitly allow **database schema and migration resets during the pre-1.0 phase**, under controlled conditions.

Policy rules:

- Migration resets (including deletion and regeneration of migration files) are allowed **only before the first stable v1.0 release**.
- Such resets must be:
  - intentional,
  - documented,
  - reproducible via scripts.
- Each reset must be accompanied by:
  - updated seed profiles,
  - passing test suites (SQLite unit tests, MySQL suite, Postman E2E),
  - updated documentation snapshots.

Once version 1.0 is released:

- Migration resets are no longer allowed.
- All schema changes must be forward-compatible and handled via additive migrations.
- Backward compatibility and upgrade paths become mandatory.

## Consequences

**Positive**

- Enables clean resolution of foundational architectural decisions (e.g. custom user model).
- Prevents accumulation of fragile or misleading migration history.
- Reduces risk of complex, error-prone data migrations during early development.
- Keeps development velocity high while core concepts are still stabilizing.

**Negative / Trade-offs**

- No guaranteed upgrade path for databases created before v1.0.
- Requires discipline to ensure resets are explicit and well documented.
- Slightly higher onboarding cost for contributors if documentation is ignored.

**Guardrails**

- Migration reset procedures must be documented (e.g. docs/architecture/migrations.md).
- Reset operations must be automated (scripts or Make targets), not manual.
- CI must always validate a clean setup from scratch (migrate → seed → test).

## Notes

This policy aligns with common practices in early-stage SaaS platforms and open-source starter kits, where schema stability is intentionally deferred until core architecture solidifies.
