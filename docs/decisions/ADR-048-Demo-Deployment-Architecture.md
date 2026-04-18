# ADR-048 Demo Deployment Architecture on Vercel, Render, Aiven, and Cloudflare R2

**Decision type**: Architecture

**Status**: Accepted

**Date**: Sprint 16

## Context

Shopwise needs a deployment architecture that:

- supports a fully presentable public demo suitable for CV/showcase use,
- preserves the current application stack without requiring immediate migration from MySQL,
- keeps frontend, backend, worker, payment mock, email preview, database, and media storage operational as separate concerns,
- remains understandable and maintainable for a solo-developer workflow,
- supports continued local development while allowing periodic redeploys of a stable public environment,
- avoids coupling the public demo to local Docker-only infrastructure.

The deployed system must reflect the current runtime architecture of the application:

- frontend is built with Next.js,
- backend is built with Django + DRF,
- async/background processing is handled by Django Q2,
- MySQL remains the source of truth for relational data,
- media files must survive redeploys,
- email-based business flows must remain demonstrable,
- payment flow must remain demonstrable using AcquireMock,
- local development must stay independent from deployed services.

The deployment architecture must also account for practical constraints discovered during implementation:

- free hosting tiers introduced operational limits that were too restrictive for the full showcase flow,
- background workers, internal networking, shell access, and always-on behavior required paid starter-level services,
- the production demo required explicit runtime logging to make failures diagnosable,
- seed data quality became a first-order operational dependency of the deployed demo.

## Decision

### 1. The public demo is deployed as a multi-service architecture

Shopwise is deployed as multiple separately managed services, not as a single monolithic host or one-process deployment.

The deployed system is composed of:

- Vercel for the public Next.js frontend,
- Render Web Service for the Django/DRF backend,
- Render Background Worker for Django Q2,
- Render Web Service for AcquireMock,
- Render Web Service for Mailpit,
- Aiven MySQL for the relational database,
- Cloudflare R2 for media file storage.

This reflects the real runtime boundaries of the application instead of collapsing all runtime concerns into one host.

### 2. Local development and deployed demo remain separate environments

Local development remains Docker-based and independent from the public deployment.

The deployed demo uses its own:

- database,
- media storage,
- service URLs,
- environment variables,
- runtime processes.

The public environment is treated as a separately deployed environment, not as an extension of local development.

Development continues locally, and the public demo is updated only through git-based redeploys.

### 3. GitHub `main` is the deployment source of truth

The monorepo stored in GitHub serves as the deployment source of truth.

Deployable parts are sourced from distinct root directories:

- `frontend/`
- `backend/`
- `acquiremock/`

The public environment is deployed from `main`.

Local and in-progress work may continue on other branches, but deployment targets the stable branch intended for demo presentation.

### 4. Frontend is deployed on Vercel

The public frontend is deployed as a Vercel project from `frontend/`.

Vercel is responsible for:

- public UI hosting,
- Next.js build/runtime,
- server-side rendering for frontend routes,
- frontend environment configuration.

The frontend communicates with the backend through the configured backend origin and API base URL.

### 5. Backend API is deployed on Render as a dedicated web service

The Django/DRF backend is deployed as a dedicated Render Web Service from `backend/`.

This service is responsible for:

- REST API,
- admin,
- authentication endpoints,
- checkout orchestration,
- payment orchestration entrypoints,
- provider integration boundaries,
- public backend routes used by the frontend.

The backend is not combined with the worker process.

### 6. Background processing is deployed as a separate Render worker

Django Q2 runs as a dedicated Render Background Worker from `backend/`.

This worker is responsible for:

- asynchronous jobs,
- scheduled jobs,
- email dispatch and similar deferred operations,
- background business workflows.

The worker is intentionally separated from the web service to preserve operational clarity and to avoid coupling long-running async processing to request-serving processes.

### 7. AcquireMock is deployed as a standalone public service

AcquireMock is deployed as a separate Render Web Service from `acquiremock/`.

It remains a standalone runtime dependency and is not embedded into the Django backend.

This preserves:

- provider isolation,
- realistic payment redirection behavior,
- demonstrable hosted mock payment flow,
- a deployment model closer to real external provider architecture.

### 8. Mailpit is deployed as a standalone public service

Mailpit is deployed as a separate Render Web Service.

It serves two purposes:

- SMTP target for application and provider emails,
- public web UI for showcasing verification links and email-based business flows.

Mailpit is intentionally exposed for demo purposes, because email-based flows are part of the showcase value of the application.

### 9. MySQL remains the database of record in deployment

The deployed demo continues to use MySQL rather than migrating to PostgreSQL.

Aiven MySQL is used as the hosted relational database because:

- it allowed the application to stay aligned with its current stack,
- it avoided migration work during the showcase phase,
- it provided a stable managed MySQL service suitable for demo deployment.

MySQL remains the source of truth for all relational business data.

### 10. Media files are stored outside the application host

Media files are stored in Cloudflare R2 through `django-storages`.

WhiteNoise is used only for static files.

This means:

- static files are served by the Django deployment through WhiteNoise,
- uploaded/generated media files are stored in object storage,
- media does not depend on Render local filesystem persistence,
- redeploys do not destroy media assets.

### 11. Production demo uses environment-specific configuration

Deployment relies on a dedicated production settings profile and deployment-specific environment variables.

In particular:

- local development uses local settings and local services,
- deployed demo uses production settings,
- storage, database, mail, payment provider URLs, and public URLs are configured through environment variables.

The same codebase is therefore reused across environments, while runtime behavior is switched by configuration.

### 12. Deployment management is operationally log-driven

The deployed environment is managed primarily through:

- service-specific logs in Render,
- deployment/runtime logs in Vercel,
- Sentry-enabled diagnostics where needed,
- Django console logging routed to Render logs.

Operational diagnosis depends on explicit backend logging at service boundaries rather than relying only on HTTP request logs.

### 13. Seed data is a first-class deployment dependency

The deployed demo depends on deterministic seed data to be functionally complete.

The seed command is not treated as optional test support only. It is part of deployment operability because the demo requires seeded:

- supplier configuration,
- tax classes,
- product prices,
- admin user,
- payment-ready data,
- scenario-ready demo data.

A stale or incomplete seed command can make an otherwise healthy deployment appear broken.

## Consequences

### Positive

- The deployed demo reflects the real runtime architecture of the application.
- The public showcase supports authentication, checkout, email, and payment demo flows.
- Media survives redeploys because it is not stored on ephemeral application disk.
- MySQL can be retained without immediate migration pressure.
- Frontend and backend can be redeployed independently.
- Local development remains intact and separate from the public environment.
- Failures can be diagnosed per service instead of treating the application as one opaque host.

### Negative

- The deployment is operationally more complex than a single-host setup.
- Multiple services must be configured and monitored consistently.
- Render starter-tier services introduce ongoing cost.
- Environment variable drift between services is a real risk.
- Public demo correctness depends heavily on seed quality.
- Some operational tasks require service-specific awareness rather than a single admin surface.

## Current Implementation

### Public frontend

- Platform: Vercel
- Source: `frontend/`
- Purpose:
  - public UI,
  - SSR/route rendering,
  - frontend-to-backend communication

### Backend API

- Platform: Render Web Service
- Source: `backend/`
- Runtime:
  - Django
  - DRF
  - Gunicorn
- Purpose:
  - API
  - admin
  - orchestration boundaries
  - provider integration entrypoints

### Background worker

- Platform: Render Background Worker
- Source: `backend/`
- Runtime:
  - Django Q2
- Purpose:
  - deferred jobs
  - scheduled jobs
  - background notifications/tasks

### Payment provider mock

- Platform: Render Web Service
- Source: `acquiremock/`
- Runtime:
  - standalone provider app
- Purpose:
  - hosted mock payment flow
  - OTP/email mock
  - payment redirect scenario

### Email preview service

- Platform: Render Web Service
- Runtime:
  - Mailpit
- Purpose:
  - SMTP target
  - email inbox UI for showcase flows

### Database

- Platform: Aiven
- Engine:
  - MySQL
- Purpose:
  - primary application data storage

### Media storage

- Platform: Cloudflare R2
- Integration:
  - `django-storages`
- Purpose:
  - product/media asset persistence outside Render local disk

### Static files

- Runtime:
  - WhiteNoise in Django
- Purpose:
  - serve static assets from backend deployment

## Deployment Topology

### Request flow

1. User opens the frontend hosted on Vercel.
2. Frontend communicates with the Django backend on Render.
3. Backend reads/writes business data in Aiven MySQL.
4. Backend stores media in Cloudflare R2.
5. Worker processes deferred jobs through Django Q2.
6. Email flows are delivered to Mailpit via SMTP.
7. Payment flow is delegated to AcquireMock.
8. Redirect/payment completion returns control back to the frontend/backend flow.

### Runtime service boundaries

- frontend does not embed backend logic,
- backend does not embed AcquireMock,
- worker does not serve HTTP requests,
- media storage is not tied to application disk,
- email preview is not embedded into backend runtime.

## Operational Rules

### 1. Local development stays local

Development continues locally using local environment files and local Docker-based services.

Local commands must not be assumed to act against the deployed environment unless explicitly configured to do so.

### 2. Deployed demo is updated by git-driven redeploy

Public deployment changes are made through repository updates and redeploys, not by editing code directly in hosting platforms.

### 3. Each service must keep its own required environment variables

A service is operational only if its own environment variables are complete.

This is especially important for:

- backend,
- worker,
- AcquireMock,
- Mailpit-related SMTP consumers.

Changing env for one service does not automatically update the others.

### 4. Managed services must be diagnosed through service-specific logs

When a public flow fails, diagnosis should begin with the logs of the service responsible for that part of the flow.

Typical examples:

- frontend rendering failures → Vercel logs
- checkout / API failures → backend logs
- async notification failures → worker logs
- payment provider failures → AcquireMock logs
- email delivery preview issues → Mailpit logs

### 5. Demo reset depends on controlled reseeding

Resetting the demo does not happen automatically on redeploy.

The database remains persistent across redeploys unless explicitly reset.

Reseeding is a separate operational action and must be performed intentionally when the demo state needs to be restored.

### 6. Seed maintenance is required after architectural changes

Whenever domain rules, supplier configuration, tax behavior, pricing, or payment assumptions change, the seed command must be updated accordingly.

Deployment stability depends on this.

## Management and Maintenance

### Environment management

The deployed environment is managed through platform environment variables rather than committed production secrets.

This includes at minimum:

- database credentials,
- storage credentials,
- backend/frontend public URLs,
- SMTP configuration,
- provider configuration,
- runtime feature toggles.

### Deployment management

Deployment is managed per service:

- Vercel for frontend,
- Render for backend, worker, AcquireMock, and Mailpit,
- Aiven for database operations,
- Cloudflare for media storage.

### Data management

Operational data management includes:

- migrations,
- seed/reset procedures,
- supplier/payment/tax configuration verification,
- admin-based inspection and correction when needed.

### Observability

Operational diagnosis depends on:

- Django console logging,
- Render logs,
- Vercel runtime logs,
- optional Sentry diagnostics.

The deployment assumes that important runtime boundaries emit explicit logs.

## Alternatives Considered and Rejected

### 1. Single-host deployment for all components

Rejected because:

- it would blur runtime boundaries,
- it would make worker/provider/email flows harder to reason about,
- it would not reflect the actual architecture of the application.

### 2. Keeping media on application filesystem

Rejected because:

- Render application disk is not the correct long-term place for demo media persistence,
- redeploy/restart safety was required,
- media should remain independent of app host lifecycle.

### 3. Immediate migration from MySQL to PostgreSQL before deployment

Rejected because:

- deployment speed was the priority,
- MySQL was already the current working stack,
- migration would delay the showcase without providing immediate demo value.

### 4. Free-tier-only hosting architecture

Rejected because:

- free-tier sleeping and service limitations made the full showcase flow unreliable,
- worker behavior, shell access, and internal communication needs exceeded practical free-tier limits,
- a stable public demo required more predictable runtime behavior.

### 5. Embedding AcquireMock or Mailpit into the backend service

Rejected because:

- it would increase coupling,
- it would make runtime management less clear,
- it would weaken the architecture as a demonstrable provider-based system.

## Recommendations for Future Work

### Short term

- harden and modernize the seed command so a full demo-ready state is produced reliably,
- improve operational logging around provider and checkout boundaries,
- document environment variables per service more explicitly,
- verify all seeded supplier, price, and tax prerequisites.

### Medium term

- move hardcoded production observability/configuration values fully into environment variables,
- add a more formal deployment runbook,
- add a repeatable reset/reseed operational procedure,
- improve health verification of cross-service flows.

### Long term

- consider consolidating or simplifying the service topology if the showcase evolves into a commercial starterkit,
- consider a future MySQL → PostgreSQL migration if platform fit or product direction requires it,
- introduce stronger deployment automation and release tracking.

## Deployment Services Summary

The current public demo is deployed as follows:

- **Frontend** → Vercel
- **Backend API** → Render Web Service
- **Background jobs** → Render Background Worker
- **Payment mock** → Render Web Service (`AcquireMock`)
- **Email preview** → Render Web Service (`Mailpit`)
- **Database** → Aiven MySQL
- **Media storage** → Cloudflare R2
- **Static files** → WhiteNoise in Django backend

This architecture is the accepted deployment model for the current Shopwise showcase environment.
