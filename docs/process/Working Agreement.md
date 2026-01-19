# Working Agreement

## Purpose

This document defines how work is executed on the Shopwise project
on a day-to-day basis.

It provides practical, operational rules that complement the
process-level decisions documented in the Process ADRs
(located in `/docs/decisions`).

The goal of this agreement is to ensure clarity, consistency,
and sustainable flow while developing a technically complex,
test-driven system as a solo developer.

---

## Delivery Model

The project follows a **Scrum-inspired iteration cadence** combined with
**Kanban-style flow management**, with **Extreme Programming (XP)**
as the technical foundation.

In practice, this means:

- Iterations (sprints) are used as **time-boxed review and inspection cycles**
- Work is managed using **pull-based flow**
- Quality, testing, and refactoring take precedence over fixed scope commitments

This model is commonly referred to as **Scrumban**, although the project
retains Scrum terminology for external clarity.

---

## Sprint Planning

- Sprints are time-boxed and have a fixed duration.
- Sprint planning is performed at the beginning of each sprint.
- The sprint backlog is **intentionally underfilled**, typically targeting
  **~60–70% of estimated capacity**.

Sprint scope is **not treated as a fixed commitment**.
Instead, the sprint represents a planning horizon and review checkpoint.

This deliberate under-allocation creates capacity for:

- unplanned but critical work,
- technical discoveries surfaced by automated tests,
- cross-cutting refactoring required to maintain system correctness.

---

## Types of Work

All work falls into one of the following explicit categories.

### Planned Feature Work

- Items selected during sprint planning.
- Typically represent user-facing functionality or planned technical improvements.
- Executed when no higher-priority work exists.

### Expedite / Blocker Work

- Critical issues that require immediate attention, such as:
  - race conditions,
  - data integrity risks,
  - CI failures,
  - test flakiness,
  - infrastructure or configuration defects.
- Can enter the sprint at any time.
- Always has priority over planned feature work.
- Is **not considered scope creep**.

### Opportunistic Pull Work

- Additional backlog items pulled when:
  - planned work is completed,
  - no expedite work exists,
  - capacity remains within the sprint.
- Selected strictly by backlog priority.

---

## Work-in-Progress (WIP)

- WIP is limited to **one primary focus item** at a time.
- Supporting activities are allowed when they directly unblock
  or complement the primary item.

Examples of supporting activities:

- code review,
- CI fixes,
- refactoring required by new findings,
- documentation updates triggered by implementation changes.

This rule is intended to minimize context switching while acknowledging
the realities of solo development.

---

## Pull Requests

Two classes of pull requests are defined to balance quality and flow.

### Lightweight PRs

Used for:

- refactoring,
- infrastructure and CI changes,
- test-only modifications,
- unblocker or expedite work.

Characteristics:

- May be created as draft PRs.
- Reviewed primarily via self-review and checklist validation.
- AI-assisted review is asynchronous and advisory.
- Typically squash-merged.

### Full Review PRs

Used for:

- new features,
- API contract changes,
- significant business logic.

Characteristics:

- TDD evidence is mandatory.
- AI-assisted review is required before merge.
- Emphasis is placed on correctness, readability, and long-term maintainability.

---

## Handling Unplanned Critical Work

Automated tests are treated as a primary feedback mechanism.

If tests reveal:

- systemic issues,
- concurrency problems,
- environment-specific defects (e.g. database-specific behavior),

the resulting work is treated as **Expedite / Blocker Work** and
takes immediate priority.

Interrupting planned work in such cases is considered
**responsible engineering practice**, not a process failure.

---

## Relationship to Quality Practices

- Test-Driven Development (TDD) is mandatory.
- Tests define correctness and drive design decisions.
- Refactoring is performed continuously, not deferred.
- Documentation gaps are treated as signals for missing tests
  or unclear system behavior.

Quality practices are further detailed in:

- `Definition of Done`
- `QA in Development`

---

## Review and Adaptation

This Working Agreement is a living document.

It may be adjusted as:

- the project evolves,
- new constraints emerge,
- tooling or delivery practices change.

Any significant changes should be reflected in a corresponding
Process ADR to preserve historical context and rationale.

---
