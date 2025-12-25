# Definition of Done

## Purpose

This document defines the **Definition of Done (DoD)** for the Shopwise project.

Its purpose is to ensure a shared understanding of when a task, story, or feature
can be considered complete from a quality perspective.

## Definition of Done

A work item is considered Done when:

- functionality is implemented according to acceptance criteria
- business rules are explicitly validated
- automated tests are implemented and passing
- existing tests are not broken
- code is readable and reasonably structured
- documentation is updated where applicable

## Testing Requirements

Testing is an integral part of Done:

- domain rules are covered by unit tests
- workflows are covered by API integration tests
- critical paths are verified via E2E tests (where applicable)

## Documentation Requirements

Documentation is part of Done when:

- public API behavior changes
- domain rules are clarified or modified
- new workflows are introduced

Documentation must reflect the current system behavior.

## CI Requirements

All automated tests must pass in CI.
Failing CI means the work item is not Done.

## Summary

Done means:

- working
- tested
- documented
- ready to be built upon safely
