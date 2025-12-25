# Design Decisions

## Purpose of This Document

This document records the **key architectural and process decisions** made during the development
of the Shopwise project.

Its purpose is to:

- preserve decision context
- explain why specific approaches were chosen
- support onboarding and future refactoring
- reduce reliance on implicit or tribal knowledge

Each decision is described using:

- context and problem statement
- the decision itself
- rationale
- consequences and impact

## 1. Adopt Test-Driven Development (TDD)

**Context / Problem**

Without tests driving development, there is a high risk that:

- business rules remain implicit
- edge cases are missed
- refactoring becomes unsafe

**Decision**

Adopt Test-Driven Development as the primary development approach for core domain logic
and critical workflows.

**Rationale**

- Forces early clarification of business rules
- Encourages small, focused units of behavior
- Provides immediate feedback during development
- Enables safe refactoring as the domain evolves

**Consequences / Impact**

- Tests act as executable specifications
- Domain rules are explicitly documented through tests
- Development speed may initially slow down but increases long-term confidence
- Strong alignment between implementation and expected behavior

## 2. Introduce Cart as a First-Class Domain Entity

**Context / Problem**

Initial designs allowed direct (and even anonymous) Order creation, leading to:

- unclear ownership
- unrealistic workflows
- weak validation boundaries

**Decision**

Introduce Cart as a dedicated domain entity representing user intent.
Restrict Order creation exclusively to Cart checkout.

**Rationale**

- Separates intent (Cart) from result (Order)
- Reflects real-world e-commerce workflows
- Provides a natural validation and control point

**Consequences / Impact**

- Cleaner domain boundaries
- Simplified Order API
- Improved testability of checkout logic
- Elimination of ambiguous order creation paths

## 3. Make Order a Read-Only Resource

**Context / Problem**

CRUD-style Order APIs allow modification of transactional data after creation,
which contradicts real-world transaction semantics.

**Decision**

Treat Order as a read-only resource from the API perspective.

**Rationale**

- Orders represent historical business decisions
- Prevents accidental or invalid modifications
- Simplifies reasoning about system state

**Consequences / Impact**

- Removal of create/update endpoints for Order
- All mutations occur indirectly (checkout, payment)
- Reduced API surface area and complexity

## 4. Introduce Explicit Cart Lifecycle (ACTIVE → CONVERTED)

**Context / Problem**

Implicit cart states made it difficult to reason about checkout correctness
and historical traceability.

**Decision**

Define an explicit and finite Cart lifecycle:

- ACTIVE
- CONVERTED

**Rationale**

- Prevents repeated or invalid checkout attempts
- Makes state transitions explicit and testable
- Supports historical analysis

**Consequences / Impact**

- Checkout becomes a one-time operation per cart
- Clear state-based validation rules
- Improved observability of cart history

## 5.Enforce “Max One ACTIVE Cart per User” via Application Logic

**Context / Problem**

Database-level constraints (e.g. OneToOne relationships) limit flexibility
and complicate future extensions such as cart history.

**Decision**

Allow multiple carts per user, but enforce at most one ACTIVE cart
using application-level validation.

**Rationale**

- Preserves cart history
- Keeps business rules explicit and readable
- Avoids overly restrictive database constraints

**Consequences / Impact**

- Clear domain rule enforced by code and tests
- Increased flexibility for future features
- Improved alignment with business logic

## 6.Introduce Fake Payment API Instead of Real Payment Integration

**Context / Problem**

Real payment gateways introduce:

- external dependencies
- non-deterministic behavior
- unnecessary complexity for a showcase project

**Decision**

Implement a Fake Payment API simulating payment outcomes.

**Rationale**

- Keeps focus on domain and workflow design
- Enables deterministic automated testing
- Avoids reliance on third-party services

**Consequences / Impact**

- Predictable and repeatable E2E scenarios
- Clear payment-related state transitions
- Solid foundation for frontend and demo use

## 7. Model Payment as an Explicit, Separate Step

**Context / Problem**

Automatically completing payment during checkout would hide
important state transitions and failure scenarios.

**Decision**

Model Payment as an explicit action performed after checkout.

**Rationale**

- Reflects real-world transactional workflows
- Makes failures explicit and observable
- Improves test coverage and reasoning

**Consequences / Impact**

- Clear Order states (CREATED, PAID, PAYMENT_FAILED)
- Easier extension for retries or refunds
- Better separation of responsibilities

## 8. Hybrid Database Strategy (SQLite for Tests, MySQL for Prod-like Setup)

**Context / Problem**

Using MySQL everywhere complicates CI;
using SQLite everywhere hides production behavior differences.

**Decision**

Adopt a hybrid approach:

- SQLite for tests and CI
- MySQL for local and production-like environments

**Rationale**

- Fast and isolated test execution
- Realistic behavior where it matters
- Reduced CI setup complexity

**Consequences / Impact**

- Stable CI pipeline
- Clear environment separation
- Explicit handling of DB-specific behavior

## 9. Enforce API Permissions Before Business Logic

**Context / Problem**

Anonymous or unauthorized access led to runtime errors
and unclear API behavior.

**Decision**

Use DRF permission checks to fail requests before business logic is executed.

**Rationale**

- Security should fail early
- Prevents leaking internal errors
- Aligns with REST and DRF best practices

**Consequences / Impact**

- Consistent 403 vs 405 behavior
- Cleaner request handling
- More predictable API responses

## 10. Treat Documentation as a Quality Tool

**Context / Problem**

Traditional documentation often becomes outdated
and disconnected from implementation.

**Decision**

Treat documentation as an active quality artifact
that evolves together with the codebase.

**Rationale**

- Improves shared understanding
- Reveals unclear or missing behavior
- Supports onboarding and cross-role communication

**Consequences / Impact**

- Documentation drives test creation
- Reduced reliance on tribal knowledge
- Better long-term maintainability

## 11. Adopt OpenAPI as Canonical API Specification

**Context / Problem**

API behavior was defined only implicitly through code and tests.

**Decision**

Use OpenAPI / Swagger as the canonical, auto-generated API specification.

**Rationale**

- Makes API surface explicit
- Integrates with testing and Postman
- Supports multiple audiences

**Consequences / Impact**

- Single source of truth for API behavior
- Easier gap analysis
- Improved onboarding experience

## 12. Prefer Workflow-Oriented Testing Over CRUD Testing

**Context / Problem**

Isolated CRUD tests do not reflect real user behavior
and provide limited confidence in business correctness.

**Decision**

Prioritize workflow-based and integration tests.

**Rationale**

- Business value lies in workflows
- Integration points carry the highest risk
- Better alignment with real usage

**Consequences / Impact**

- Fewer but more meaningful tests
- Higher confidence in core flows
- Clear mapping between tests and business rules

## Summary

The design decisions documented here shape Shopwise as a
workflow-driven, quality-focused backend system.

They emphasize:

- explicit rules over implicit behavior
- clarity over convenience
- documentation and tests as first-class artifacts
