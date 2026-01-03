# Postman CLI in CI – Current Pipeline Setup (Snapshot)

This document describes the **current, working setup** of Postman CLI execution in CI.  
It is intended as a **snapshot of the architecture**, understandable by **testers and project managers**, not only developers.

The goal of this setup is to:

- run Postman API tests automatically in CI
- test a real running backend
- use a real database (MySQL)
- fail fast and visibly when API behavior breaks

---

## High-Level Overview

**What we are testing**

- Backend API built with **Django / Django REST Framework**
- Authentication and business endpoints via **Postman collections**

**How tests are executed**

- CI platform: **GitHub Actions**
- API tests runner: **Postman CLI**
- Collections & environments: **Postman Cloud (by ID, not JSON files)**
- Database: **MySQL (service container, ephemeral)**

---

## Architecture at a Glance

GitHub Actions Job

│

├── MySQL service (clean DB per run)

│

├── Django backend

│ ├── migrate database

│ ├── seed test data (users, etc.)

│ └── runserver (localhost:8000)

│

└── Postman CLI

└── runs cloud collection against local backend

Key principle:

- **Postman CLI does not start the backend or prepare data**.
- **CI must prepare everything explicitly before running tests.**

## Postman CLI Execution Model

### What is used

- **Postman CLI GitHub Action**

  - postmanlabs/postman-cli-action@v1

- Collections are referenced by **Postman Cloud collection ID**
- Environments are referenced by **Postman Cloud environment ID**

This means:

- No `.json` collections committed to the repo
- CI always runs the **latest saved version** from Postman Cloud

## CI Job Responsibilities (Clear Separation)

### CI responsibilities

- provisioning database
- migrating schema
- seeding test data
- starting backend server
- running Postman CLI
- collecting reports

### Postman responsibilities

- defining API requests
- assertions / tests
- request chaining and variable handling
- validating API behavior

## Database Setup in CI

### Database Type

- **MySQL 8** via GitHub Actions service container

### Important characteristics

- Database starts **empty on every run**
- Data exists **only for the duration of the job**
- Database is destroyed after the job finishes

### Implication

> **Any data required by Postman tests (e.g. users) must be seeded explicitly.**

## Django Backend Preparation Steps

The CI job prepares the backend in the following order:

1. **Install dependencies**
2. **Wait for MySQL service to be ready**
3. **Run database migrations**
4. **Seed test data**
5. **Start Django development server**
6. **Verify backend health**
7. **Run Postman CLI tests**

### Why this order matters

- Seeding before migrations → fails
- Running Postman before seeding → login fails
- Running Postman before server is ready → connection errors

## Test Data Seeding

### Seed command

A custom Django management command is used:

```bash
python manage.py seed_test_data
```

#### Purpose of the seed

- create required test users (e.g. customer_2)
- set passwords correctly using Django hashing
- prepare minimal data needed for API flows

#### Seed location in pipeline

- Runs **after migrations**
- Runs **before starting the server**

This ensures:

- backend and Postman CLI see the **same database state**

## Backend Runtime in CI

### Server mode

- Django `runserver`
- Runs in background
- Bound to `127.0.0.1:8000`

### Why localhost is used

- Postman CLI runs in the same CI runner
- No external networking needed
- Faster and simpler setup

## Healthcheck Strategy

Before running Postman CLI:

- CI performs a simple HTTP healthcheck
  = Confirms backend is reachable

Example:

```http
GET /api/v1/health/
```

If healthcheck fails:

- Postman tests are not meaningful
- CI should fail early

## Postman CLI Configuration

### Execution method

Postman CLI is executed using cloud IDs:

```
collection run <COLLECTION_ID>
--environment <ENVIRONMENT_ID>
```

### Reporters

- `cli` – human-readable output in CI logs
- `junit` – machine-readable test results

JUnit report is stored as a CI artifact.

## Postman Environments

### Environment source

- Stored and managed in **Postman Cloud**
- Referenced in CI by **environment ID**

### Best practices

- Use consistent variable names (e.g. `base_url`)
- Avoid mixing `baseUrl` / `base_url`
- Store secrets securely (Postman + GitHub Secrets)
- Assume CI always runs with **clean state**

## Authentication Strategy

Login request uses:

```pgsql
Content-Type: application/json
```

- No Postman-level authentication is enabled
- Tokens (if any) are handled explicitly in requests/scripts

This keeps authentication logic transparent and debuggable.

## Debugging Philosophy

When tests fail:

1. **Test with curl inside CI**

- confirms backend vs Postman responsibility

2. **Verify DB contents**
   - user existence
   - password correctness
3. **Only then debug Postman scripts**

This avoids wasting time debugging the wrong layer.

## What This Setup Guarantees

- ✅ Reproducible test runs
- ✅ No dependency on local developer data
- ✅ Clear separation of concerns
- ✅ Failures point to real issues (API, data, or logic)
- ✅ Easy onboarding for testers and PMs

## Key Takeaway

> **Postman CLI in CI is only as reliable as the environment you prepare for it.
> CI must create the world that Postman tests expect.**

This document represents the current, working baseline and should be updated whenever:

- database type changes
- seed logic changes
- Postman execution model changes
