# System Architecture – Shopwise

This document describes the high-level architecture of the Shopwise system,
including its main components, responsibilities, and interactions.

The goal is to provide a clear understanding of how the system is structured
and how individual parts communicate.

## High-Level Architecture

Shopwise follows a classic client-server architecture:

- Frontend: React + TypeScript
- Backend: Django + Django REST Framework
- Database: MySQL
- Deployment: Docker + Render
- CI/CD: GitHub Actions

Frontend communicates with the backend exclusively via REST API.
The backend is responsible for business logic, data persistence,
authentication, and integrations.

## Architecture Diagram (Logical)

[ Browser ]
|
| HTTPS (REST API)
v
[ React Frontend ]
|
| JSON over HTTP
v
[ Django REST API ]
|
| ORM
v
[ MySQL Database ]

Administrative functionality is handled via Django Admin
and is not exposed to the frontend application.

## Backend Architecture

The backend is implemented using Django and Django REST Framework.
It follows a layered architecture:

- API Layer (Views / ViewSets)
- Service Layer (business logic)
- Domain Models (Django models)
- Persistence Layer (MySQL via ORM)

Business logic is intentionally separated from views
to improve testability and maintainability.

Backend layers:

backend/
apps/
users/
products/
categories/
discounts/
orders/
payments/

Each app is responsible for its own models, serializers,
services, and tests.

## Frontend Architecture

The frontend is a Single Page Application built with React and TypeScript.
It is responsible for:

- Rendering UI
- Managing client-side state
- Communicating with backend API

Basic implementation proposal:

frontend/
src/
api/
components/
pages/
hooks/
tests/

The frontend does not contain business logic.
All validations and rules are enforced on the backend.

## Data Architecture

- Relational database (MySQL)
- Normalized schema
- Referential integrity enforced at database level

All data access is handled through Django ORM.
No direct SQL queries are used in application logic.

### Database Usage by Environment

- Local development: MySQL
- CI unit tests: SQLite
- CI integration tests: MySQL
- Production: MySQL

## Authentication & Authorization

- Authentication is handled by Django authentication system
- Token-based authentication for REST API
- Role-based access:
  - Admin
  - Customer

Admin users manage the system via Django Admin interface.
Customers interact via frontend application.

## Payment Architecture (Mocked)

Payments are implemented as a mocked internal service.
No real payment provider is integrated.

The payment service simulates:

- successful payment
- failed payment

This approach allows testing of:

- payment workflows
- error handling
- order state transitions

## CI/CD

CI/CD pipeline is implemented using GitHub Actions.

Pipeline includes:

- backend tests
- frontend tests
- build
- deployment to Render

Detailed CI/CD description is available in:
docs/ci-cd/pipeline.md## Architectural Principles

- Separation of concerns
- Testability first
- Automation over manual processes
- Explicit documentation
- Simplicity over premature optimization

## Non-functional Requirements

- Maintainability
- Testability
- CI/CD automation
- Clear documentation
- Deterministic deployments

## Out of Scope

- Real payment gateway
- Mobile application
- Advanced scalability (microservices)
