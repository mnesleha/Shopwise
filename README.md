# Shopwise

**The Shopwise development showcase project.**

Shopwise is a demo e-commerce project designed as a **quality-driven showcase**.
Its primary goal is to demonstrate how backend/frontend development, testing, documentation,
and QA processes can work together as equal partners.

The project focuses not only on _what_ is built, but also on _how_ and _why_ it is built.

## Project Purpose

Shopwise was created as a portfolio and learning project with a clear focus on:

- backend domain design
- API-first development
- automated testing at multiple levels
- documentation as a quality and communication tool
- QA involvement throughout the entire development lifecycle

## What This Project Demonstrates

This project demonstrates the ability to:

- design a realistic backend domain (products, cart, orders, payments)
- expose domain logic through a REST API
- cover business rules with automated tests (unit, integration, E2E)
- simulate real-world workflows (checkout, payment)
- use documentation as an active part of quality assurance
- work with CI pipelines and development workflows

## Target Audience

The documentation and structure of this project are intentionally designed
to be understandable for multiple roles:

- Recruiters – to quickly understand the scope and intent of the project
- Project Managers – to see how development, QA, and documentation fit together
- Test / QA Managers – to evaluate testing strategy, quality gates, and processes
- Developers – to explore the technical implementation details

## High-Level Domain Overview

Shopwise models a simplified e-commerce workflow:

- Product & Category catalog
- User Cart as an expression of user intent
- Order created exclusively via checkout
- Fake Payment API simulating payment outcomes

The system intentionally avoids unnecessary complexity
while preserving realistic domain boundaries.

## Documentation

Detailed documentation is available in the `docs/` directory and is structured
by topic and audience.

Key entry points:

- Architecture Overview
- Domain Model & Lifecycle
- Testing Strategy
- API Documentation (OpenAPI / Swagger)
- QA & Development Process

## Tech Stack (High-Level)

- Python, Django, Django REST Framework
- MySQL (production-like), SQLite (tests)
- Pytest
- GitHub Actions
- Postman

## Current Project Status

The project is actively developed using Scrum-inspired iterations.

Current focus:

- backend API stabilization
- documentation-driven quality improvements
- OpenAPI / Swagger documentation

Planned:

- frontend exploration (React)
- frontend testing (Playwright)

## Repository Structure

- `backend/` – Django backend application
- `docs/` – project documentation
- `.github/` – CI configuration

## Final Note

Shopwise is not intended to be a production-ready e-commerce system.
Its primary purpose is to demonstrate thoughtful engineering,
quality-focused development, and clear communication.
