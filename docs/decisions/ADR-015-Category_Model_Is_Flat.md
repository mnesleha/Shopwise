# ADR-015 Category Model Is Flat (No Hierarchy)

**Status**: Accepted

**Date**: Sprint 7

**Decision type**: Architecure

## Context

Shopwise historically modeled categories as a two-level tree (parent → children). This is reflected in:

- the `Category` model (`parent` FK + `is_parent` flag + validation rules)
- API documentation/examples returning nested `children` structures

This design accumulated historical churn (added → removed → re-added → removed). As a result, old migrations contain constraints that are no longer aligned with the intended domain.

When running migrations on MySQL, a historical CHECK constraint fails early in the migration chain (around categories migration \#0002), preventing database setup and blocking MySQL test execution. This issue does not surface on SQLite, which is more permissive in this area.

Additionally, upcoming work is shifting discount semantics toward “promotions/campaigns” that can target multiple products explicitly. In such a model, category hierarchy provides limited value but significantly increases complexity in:

- migrations and cross-db support
- serialization and OpenAPI contract
- test data generation and deterministic seeding
- discount applicability rules (parent vs leaf behavior)

## Decision

We will treat product categories as a **flat list** (no hierarchy).

- Remove the category hierarchy concept (`parent`, `is_parent`, `children`).
- Categories remain read-only classification labels.
- Any grouping logic needed for discounts/promotions will be handled by explicit campaign/promotion targeting (e.g., “this promotion applies to these products”), not by traversing a category tree.

**Principles**:

- Simplify the domain to match actual project needs (demo e-commerce workflow + QA showcase).
- Enable MySQL parity by removing legacy migration constructs that block migrations.
- Prefer explicit product targeting for promotions over implicit hierarchy-based rules.
- Keep API contract stable and predictable (flat categories are simpler for FE and tests).

## Consequence

**Positive**

- MySQL migrations become runnable (unblocks MySQL test suite).
- Category API and OpenAPI contract become simpler (no nested serialization).
- Seed/test data becomes easier to manage deterministically.
- Promotions (campaigns targeting multiple products) become the primary mechanism for discount grouping.
- Removes “leaf vs parent” edge cases in discount rules.

**Negative**

- Breaking change to category API response shape (removes children and is_parent).
- Requires updating:
  - serializers/views/OpenAPI examples
  - Postman collections and any contract tests referencing category tree
- If true hierarchical navigation is needed later, it must be reintroduced deliberately with a clean migration strategy.
