## Summary

- What does this PR change and why?

## TDD Workflow Context (Instructions for Reviewer)

This Pull Request follows the **Test-Driven Development (TDD)** methodology. Please provide reviews incrementally based on the current phase indicated by the latest commits:

1. **RED Phase (commits with `test:` prefix):**

   - Focus exclusively on test quality, readability, and edge-case coverage.
   - **Ignore CI test failures** – they are intentional at this stage.
   - Verify if the tests correctly define the expected behavior.

2. **GREEN Phase (commits with `feat:` or `fix:` prefix):**

   - Review the logic implementation.
   - Ensure the code satisfies the requirements defined by the tests.
   - Cleanliness is important, but focus primarily on functionality here.

3. **REFACTOR Phase (commits with `refactor:` prefix):**
   - Focus on code quality, Clean Code principles, performance, and standards.
   - This is the stage for your final and most rigorous review.

**Communication Instructions:**

- Provide all feedback as comments directly within this Pull Request.
- **Do not create a new Pull Request** for subsequent phases; all work stays here.
- If the current phase is RED, please provide feedback like "Tests are logically sound" or "Missing test case for XY" instead of reporting code errors.

## Jira

- Issue: SHOP-XXX

## Testing

- [ ] `pytest`

## Test Coverage Notes

- What scenarios are covered? (happy path + edge cases)

## Documentation

- [ ] Docs updated (if behavior/API changed)

## Quality Checklist

- [ ] TDD followed (tests added/updated first or alongside change)
- [ ] No secrets committed
- [ ] Code is readable and maintainable (naming, structure)
- [ ] CI is green (required before merging)

## Risks / Rollback

- Any notable risks?
- How to revert if needed?
