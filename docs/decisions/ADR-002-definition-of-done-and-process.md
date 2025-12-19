# Definition of Done

A user story is considered "Done" when all of the following
criteria are met:

- Code is implemented according to acceptance criteria
- Code is committed to the main branch
- Automated tests are written and passing
- CI pipeline is green
- Documentation is updated
- Code follows agreed coding standards

Stories that do not meet all DoD criteria
must not be marked as Done.

## Branch Strategy

The project uses a simplified Git flow suitable for small teams.

Branches:

- main
- feature/\*

- The main branch always contains stable, deployable code
- Each user story is implemented in a separate feature branch

Workflow:

1. Create feature branch from main
2. Implement changes
3. Push branch and open Pull Request
4. CI pipeline runs
5. Review and merge to main

## Code Review Process

All changes must go through a Pull Request.

Review Checklist:

- Code matches acceptance criteria
- Tests cover critical logic
- No obvious code smells
- Documentation updated if needed

Even in a single-developer setup,
the review process is simulated
to enforce quality standards.

## Rationale

This process ensures:

- Consistent code quality
- Early detection of defects
- Traceability of changes
- Alignment with Scrum principles

## ADR Metadata

Status: Accepted  
Date: 2025-12-19  
Decision Makers: Product Owner, Developer
