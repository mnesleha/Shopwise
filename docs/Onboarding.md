# Shopwise – Onboarding Document

## Purpose of This Document

This document serves as the primary onboarding and context-setting artifact for the Shopwise project.

Its goals are:

- to provide a clear understanding of **what is being built and why**
- to explain **how development, testing, and documentation are integrated**
- to enable a new team member (developer, QA, or PM) to become productive quickly
- to act as a stable knowledge anchor when continuing work in a new context (e.g. new sprint, new discussion thread)

This document intentionally focuses on **concepts, decisions, and workflows**, not implementation details.

## What Is Shopwise

Shopwise is a demo e-commerce backend project built as a **quality-driven showcase**.

The project models a simplified but realistic e-commerce workflow:

- product and category catalog
- user cart representing intent
- order creation via checkout
- simulated payment processing

The system is not intended to be production-ready.
Its primary purpose is to demonstrate **thoughtful backend design, testing strategy, documentation practices, and QA involvement throughout development**.

## Why Shopwise Exists

Shopwise was created to demonstrate that:

- backend domain design goes beyond CRUD
- testing is part of design, not a post-development activity
- documentation can actively drive quality and reveal gaps
- QA is an equal partner in development, architecture, and communication

The project intentionally emphasizes _how_ and _why_ things are built, not just _what_ is built.

## Technology Stack

Backend:

- Python
- Django
- Django REST Framework (DRF)

Databases:

- MySQL – production-like environment
- SQLite – fast, isolated test execution

Testing:

- Pytest – unit and API integration tests
- Postman – E2E and workflow verification

CI:

- GitHub Actions – automated test execution

Documentation:

- Markdown-based documentation
- OpenAPI / Swagger (drf-spectacular)

Frontend (planned):

- Vite
- React
- Vitest
- React Testing Library

## Development Methodology

Shopwise follows a Scrum-inspired, iterative approach with strong emphasis on quality practices.

### Core principals

- **Test-Driven Development** (TDD)

  Business rules are validated by tests before and during implementation.

- **Documentation-Driven Development** (DDD\*)
  Documentation is used to:

  - explain intent
  - validate API consistency
  - reveal missing tests and unclear behavior

- **Incremental refinement**

  Architecture and domain decisions are revisited as understanding evolves.

\*DDD here refers to Documentation-Driven Development, not Domain-Driven Design, although domain modeling principles are applied

## Domain Model

The core domain entities are:

- Product
- Category
- Cart
- CartItem
- Order
- Payment

### Cart

- Represents user intent
- A user can have at most one ACTIVE cart
- Cart lifecycle:
  ACTIVE → CONVERTED

### Order

- Represents the result of checkout
- Orders are immutable from the API perspective
- Orders are created exclusively via cart checkout
- Orders are read-only resources

### Payment

- One-to-one relationship with Order
- Simulates payment processing
- Possible outcomes:
  SUCCESS
  FAILED

This separation ensures a clear distinction between **intent (Cart)** and **result (Order)**.

## API Overview and Workflow

The API is designed around workflows rather than isolated resources.

### Cart

- GET /api/v1/cart/
  Retrieves or creates the active cart for the user.

- POST /api/v1/cart/items/
  Adds an item to the active cart.

- POST /api/v1/cart/checkout/
  Converts the cart into an order.

### Orders (Read-Only)

- GET /api/v1/orders/
  Lists user orders.

- GET /api/v1/orders/{id}/
  Retrieves order details.

### Payments

- POST /api/v1/payments/
  Simulates payment for a given order.

## End-to-End Workflow

A typical E2E scenario follows this sequence:

1. User retrieves active cart
2. User adds items to cart
3. User performs checkout
4. Order is created from cart
5. Payment is simulated
6. Order status is updated based on payment result

This workflow is covered by:

- automated API tests (pytest)
- Postman E2E collection

## Testing strategy

Shopwise follows a test pyramid approach:

- Unit tests

  Validate domain rules and invariants (models).

- API integration tests

  Validate workflows, permissions, and state transitions.

- E2E tests (Postman)

  Validate realistic user flows across multiple endpoints.

  Key testing tools:

- Pytest

  Primary automated testing framework.

- Postman

  Executable documentation and E2E verification.

## Documentation Methodology

Documentation is treated as a quality and communication tool.

- README.md
  Entry point and project overview.

- docs/
  Structured documentation by topic and audience.

- OpenAPI / Swagger
  Auto-generated API documentation used to:
  - inspect API completeness
  - identify undocumented behavior
  - reveal missing test coverage

Documentation gaps are intentionally treated nad used as input for further dvelopment.

## Next steps

Planned upcoming work includes:

- OpenAPI / Swagger integration and refinement
- Documentation-driven identification of missing tests
- Frontend exploration using:
  - Vite
  - React
  - Vitest
  - React Testing Library

Frontend work will build on a stable, documented and test-covered backend.

## How to Continue Work

To continue work on this project:

1. Review this onboarding document
2. Explore the docs/ directory
3. Review existing tests and Postman collections
4. Use Swagger/OpenAPI as a reference for API behavior

This document is intended to provide enough context to continue development without relaying on historical discussions.
