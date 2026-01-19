# Scrum & Workflow

## Purpose

This document describes the **development workflow** used in the Shopwise project.

## Process Overview

Shopwise follows a Scrum-inspired, iterative workflow.

The process is intentionally lightweight and adapted
to a single-developer / showcase context.

## Sprint Cadence

- Sprints have a fixed duration.
- A sprint represents a review and inspection cycle, not a fixed scope commitment.
- Work may flow in and out of the sprint according to priority rules
  defined in the Working Agreement.

## Sprint Planning

Sprint planning is performed at the start of each sprint.

During planning:

- High-priority backlog items are reviewed.
- A limited set of items is selected into the sprint backlog.
- The sprint backlog is intentionally underfilled.

Outputs:

- Sprint backlog (initial)
- Clear understanding of current priorities and risks

## During the Sprint

During the sprint:

- Work is pulled according to priority.
- Expedite / Blocker work may interrupt planned work at any time.
- Only one primary work item is actively developed at a time.

Activities include:

- implementation and refactoring,
- automated testing,
- CI/CD maintenance,
- documentation updates when required.

Sprint scope may evolve as new information is discovered.

## Sprint Review

At the end of the sprint:

- Completed work is reviewed.
- Delivered functionality and technical improvements are demonstrated.
- Outstanding or interrupted work is assessed and reprioritized.

The review focuses on:

- outcomes,
- quality,
- learnings,
  not on adherence to the original sprint scope.

## Backlog Management

- Product backlog is maintained in Jira
- Stories are refined and estimated before implementation
- Technical and documentation tasks are treated as first-class backlog items

## Development Flow

Typical workflow:

1. Select story from sprint backlog
2. Clarify acceptance criteria
3. Write or update tests
4. Implement functionality
5. Refactor if needed
6. Update documentation
7. Verify via CI

## Sprint Retrospective

After the sprint review:

- Process effectiveness is briefly evaluated.
- Friction points, bottlenecks, and recurring issues are identified.
- Concrete improvement actions are defined when needed.

Retrospective outcomes may result in:

- Working Agreement updates,
- new Process ADRs,
- backlog adjustments.

## Summary

The workflow prioritizes:

- clarity over speed
- quality over output
- continuous improvement
