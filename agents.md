# AGENTS.md

## Project overview

This repository contains a Django backend with a REST API, project documentation, and API testing artifacts.

Repository structure:

- `backend/` — Django + Django REST Framework backend
- `backend/venv/` — local Python virtual environment (must not be modified by agents)
- `docs/` — project documentation (Markdown)
- `postman/` — exported Postman collections (JSON)

Primary goals:

- Deliver backend features incrementally
- Keep API behavior explicit and predictable
- Maintain tests and documentation as first-class artifacts

---

## Runtime & environment

### Python

- Python version: **3.14.1**
- Dependency management: **venv + pip**
- Virtual environment location: `backend/venv/`
- Dependencies are defined in: `backend/requirements.txt`

Rules:

- Do not modify `backend/venv/`
- If dependencies change, update `requirements.txt` only

---

## Local development

### Run backend

```bash
cd backend
python manage.py runserver
```

## Databases

- SQLite: local development & automated tests
- MySQL: manual API testing via Postman and production parity
- Both databases run locally

Rules:

- Default to SQLite unless explicitly instructed
- Avoid DB-specific SQL unless required
- Clearly document MySQL-specific behavior when introduced

## Testing

### Unit tests

- Framework: pytest
- Command:

```bash
cd backend
pytest
```

Testing philosophy:

- Cover both happy paths and relevant edge cases
- Add tests when changing behavior
- Tests are expected to evolve and improve over time

## API & OpenAPI documentation

- OpenAPI generation: **drf-spectacular**
- Schema endpoint: `/api/schema`
- Swagger UI: `/api/docs/swagger/`
- Redoc: `/api/docs/redoc/`

Rules:

- OpenAPI schema is generated automatically
- Do not manually edit generated schema artifacts
- When endpoints, serializers, or permissions change:
  - Ensure schema remains valid
  - Explicitly note any breaking changes

## Django & DRF conventions

### Views

- Allowed view types:
  - `APIView`
  - `ReadOnlyModelViewSet`
  - `ModelViewSet`
- Prefer consistency with existing patterns over introducing new abstractions

### Business logic

- Business logic currently lives **directly in views**
- Do not introduce service layers or architectural refactors unless explicitly requested

## Authentication & permissions

- Authentication: **Django sessions**

- Permissions:
  - Currently defined ad-hoc per view (permission_classes)
  - Common patterns include [IsAuthenticated] or empty lists

Rules:

- Do not introduce new permission systems without discussion
- If touching permissions:
  - Make behavior explicit
  - Highlight security implications
  - Suggest improvements separately (do not silently refactor)

## Documentation (`docs/`)

Key documents:

- `docs/onboarding.md` — onboarding and working conventions
- `docs/readme.md` — documentation index
- `docs/architecture/` — evolving architecture notes

Rules:

- Update documentation when behavior, API, or setup changes
- Keep docs factual and concise
- Architecture docs should reflect current state, not future plans

## Postman collections (`postman/`)

- JSON exports from Postman
- Used for manual API testing against MySQL

Rules:

- Do not modify Postman collections unless explicitly requested
- If API changes affect Postman tests:
  - Clearly note required updates

## Code & change discipline

1. **Small, focused changes**

   - Prefer incremental commits
   - Avoid large refactors unless explicitly requested

2. **Respect existing patterns**

   - Follow current Django app structure
   - Reuse serializers, views, and permission patterns
   - Avoid introducing new architectural layers implicitly

3. **Migrations**

   - Avoid unnecessary schema migrations
   - Clearly explain intent and impact when migrations are required

4. **Safety & clarity**

   - Assume code may run in production
   - Be explicit about risks, edge cases, and backward compatibility

## Continuous Integration (GitHub Actions)

- GitHub Actions CI is enabled
- **All checks must pass**
- CI is authoritative:
  - tests
  - formatting
  - any additional configured checks

## Output expectations (for agents & reviews)

For any non-trivial change, provide:

- Summary of what changed and why
- List of files modified
- How to test the change (exact commands)
- Notes on:

  - migrations
  - API compatibility
  - documentation or Postman updates
