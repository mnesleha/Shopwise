# Git Branching & Pull Request Workflow

Shopwise uses a **trunk-based development** workflow.

## Branching Rules

- `main` is always **release-ready** (green CI, deployable).
- All changes must be made in a **short-lived branch** and merged via **Pull Request**.
- Direct pushes to `main` are not allowed (protected branch).

### Creating Branches (Jira → GitHub)

Shopwise branches are created from Jira issues using the **"Create branch"** action.

Workflow:

1. In Jira, open the issue and click **Create branch** (GitHub).
2. Use `main` as the base branch.
3. Fetch and check out the branch locally:

```bash
git checkout main
git pull origin main
git fetch origin
git checkout -b <branch-name> origin/<branch-name>
```

### Branch Naming Convention

Use one of the following formats:

- `feature/<short-description>`
- `bugfix/<short-description>`
- `chore/<short-description>`
- (optional) include Jira key: `feature/SW-123-<short-description>`

Examples:

- `feature/pricing-discounts`
- `bugfix/cart-total-rounding`
- `chore/update-ci`

## Pull Request Rules

Every branch must be merged via a Pull Request targeting `main`.

PRs must include:

- A clear title and description of the change
- Link to the related Jira issue (if applicable)
- Testing notes (how to verify)

### When to Open a Pull Request

Open a Pull Request **early** (as a Draft) after the first meaningful commit (often the initial failing tests in TDD).
This enables:

- continuous CI feedback during development
- an auditable change history (tests → implementation → refactor → docs)
- easier review and clearer scope control

Mark the PR as **Ready for review** only when:

- automated tests are green
- CI checks pass
- documentation is updated (if behavior/API changed)

### PR Checklist

- [ ] Automated tests added/updated (TDD)
- [ ] Local tests are green (backend + frontend)
- [ ] CI pipeline is green
- [ ] Documentation updated (when behavior/API changes)
- [ ] No secrets or sensitive data committed

## Merge Strategy

Use **Squash and merge** to keep a clean, readable commit history.

After merge:

- Delete the remote branch
- Sync local `main` with `git pull origin main`
