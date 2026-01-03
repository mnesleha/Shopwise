# ADR-014: Dual Database Testing Strategy (SQLite Default, MySQL Verification Suite)

**Status**: Accepted

**Date**: Sprint 7

**Decision type**: Architecure

## Context

The project currently runs the pytest suite against **SQLite** by default. This provides fast feedback but introduces a risk of **false confidence**, because production will run on MySQL where behavior differs in important ways:

- **Transactions & isolation**: SQLite locking/concurrency semantics can mask race conditions or rollback edge cases that appear under MySQL.
- **Constraints & indexes**: foreign keys, unique constraints, collations, and length semantics may behave differently or depend on configuration.
- **Datetime/timezone**: storage and comparison precision differs (e.g., microseconds, timezone handling).
- **JSON/text fields**: MySQL has native JSON; SQLite typically stores JSON-like content as text.
- **DB error codes**: Integrity/concurrency errors differ by backend and may affect error-to-API mapping and conflict handling.

As the project hardens critical flows (checkout → order → payment), relying on SQLite-only testing increases the probability of production-only defects and regressions that are hard to detect early.

## Decision

We adopt a **dual-database testing strategy**:

- **SQLite remains the default** database backend for the majority of the test suite to preserve fast developer feedback.
- A targeted **MySQL verification suite** is introduced to validate correctness in areas where SQLite is known to diverge from MySQL semantics.

### Test Markers

We introduce explicit pytest markers:

- `@pytest.mark.sqlite` — safe to run on SQLite (default suite)
- `@pytest.mark.mysql` — must be verified on MySQL (selective suite)

Default invocation:

- Run fast suite (SQLite):
  - `pytest -m "not mysql"`

MySQL verification suite:

- `DJANGO_SETTINGS_MODULE=settings.local pytest -m mysql`

### Scope and When to Run MySQL Tests

MySQL tests are required when changes touch:

- checkout/order/payment flows,
- pricing snapshot persistence,
- transaction/atomicity boundaries,
- model constraints/migrations,
- error mapping that depends on database exceptions.

## MySQL Suite Focus

The MySQL-marked tests must prioritize known divergence areas:

- atomicity and rollback (no partial persistence on failure),
- decimal precision and rounding persistence,
- foreign key / integrity enforcement,
- conflict and idempotency behavior (e.g., “payment cannot be created twice”),
- datetime precision/timezone invariants,
- database-originated exceptions mapped to API errors.

### Principles

- **Fast feedback first**: SQLite suite must stay fast and run continuously.
- **Reality check for critical flows**: MySQL suite ensures production parity where it matters.
- **Selective redundancy**: only tests covering DB-dependent behavior require MySQL; business logic tests remain database-agnostic.
- **Explicitness**: tests declare the expected DB context via markers.

## Consequences

**Positive**

- Reduces “works on SQLite” false positives and production-only bugs.
- Improves confidence in checkout/order/payment hardening and pricing snapshot behavior.
- Makes database assumptions explicit and auditable (valuable for architecture reviews).
- Enables CI pipelines to balance speed (SQLite) and correctness (MySQL) using targeted runs.

**Negative**

- Requires maintaining two test execution modes and environments.
- MySQL suite runs slower and introduces more CI complexity (e.g., service containers, credentials).
- Some tests may need careful design to avoid flakiness (especially concurrency/race-condition checks).
