# ADR-0XX: Delivery Model Adjustment – Scrum to Scrumban (XP-driven)

**Status**: Accepted

**Date**: Sprint 10

**Decision type**: Process

**Scope**: Delivery methodology, sprint planning, work prioritization, WIP limits, pull request workflow

---

## Context

This project is developed by a single developer in a QA/SDET role, using a strong **Test-Driven Development (TDD)** and **Extreme Programming (XP)** approach, with significant assistance from AI tools.

The system under development exhibits **cross-cutting technical characteristics**, including:

- database concurrency and transactional consistency,
- CI/CD infrastructure and test automation,
- interactions across multiple bounded contexts (cart, pricing, orders, payments).

In recent sprints, critical technical issues (e.g. database race conditions specific to MySQL behavior) were discovered **only through automated tests**, despite the same functionality behaving correctly under SQLite.  
Such issues required **immediate investigation and resolution**, as postponing them would risk data corruption or invalid system behavior.

Under a strict Scrum delivery model with full sprint commitment:

- unplanned but critical work repeatedly entered the sprint,
- sprint scope was frequently disrupted,
- sprint delivery formally appeared as "incomplete", despite correct technical prioritization.

A concrete example is documented in **[ADR-026 (ActiveCart Pointer Refactor)](./ADR-026-ActiveCart-Pointer-Refactor.md)**, where test-driven discovery of a MySQL race condition required urgent cross-cutting refactoring that was not part of the original sprint scope.

This revealed a structural mismatch between:

- the realities of XP-driven, test-first development in a technically complex system,
- and a rigid interpretation of Scrum sprint commitments.

---

## Decision

The project formally adopts a **Scrumban delivery model with XP as the technical core**, while retaining Scrum ceremonies for planning and review.

The following adjustments are introduced:

### Sprint Planning

- Sprint backlogs are **intentionally underfilled**, typically targeting **~60–70% of estimated capacity**.
- The sprint is treated as a **time-boxed review and inspection cycle**, not a fixed scope commitment.

### Classes of Work

Work is explicitly categorized into three classes:

1. **Planned Feature Work**

   - Defined during sprint planning.
   - Represents business or product-facing functionality.

2. **Expedite / Blocker Work**

   - Includes critical defects, race conditions, CI failures, test flakiness, or data integrity risks.
   - Can enter the sprint **at any time**.
   - Has absolute priority over planned work.
   - Is **not considered scope creep**.

3. **Opportunistic Pull Work**
   - If planned work is completed and no expedite work exists,
   - additional backlog items may be pulled based on priority (Kanban pull principle).

### Work-in-Progress (WIP)

- WIP is limited to **one primary focus item** at a time.
- Supporting activities (reviews, infrastructure fixes, unblockers) are allowed as secondary tasks, provided they serve the primary focus.

### Pull Request Policy

Two classes of pull requests are defined:

- **Lightweight PRs**

  - Used for refactoring, infrastructure, test-only changes, or unblocker work.
  - May use draft PRs and asynchronous AI review.
  - Squash-merged after checklist-based self-review.

- **Full Review PRs**
  - Used for new features, API contract changes, or significant business logic.
  - Require full TDD evidence and structured AI-assisted review before merge.

This distinction reduces administrative overhead while preserving quality guarantees.

---

## Consequences

### Positive

- Immediate response to critical technical issues without violating process rules.
- Better alignment with TDD, XP, and testing-first development.
- Reduced occurrence of "false sprint failure" caused by responsible technical intervention.
- Clear audit trail through ADRs, tests, and pull requests.

### Trade-offs

- Reduced predictability of feature delivery at sprint scope level.
- Increased reliance on continuous backlog prioritization.
- Requires discipline in WIP management and explicit work classification.

---

## Notes

- This decision does not remove Scrum ceremonies (planning, review, retrospective), but reframes their purpose.
- The delivery model reflects the realities of solo development in a technically complex, test-driven system.
- Working Agreement and Jira workflow definitions are updated to reflect this ADR.

---
