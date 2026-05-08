# Product Vision

## Purpose

This document describes the product intent of **Shopwise**.

It explains:

- what the project is
- why it exists
- what kind of product it is evolving into
- what problem space it addresses
- what is currently in scope
- what is intentionally out of scope

---

## 1. What Shopwise Is

Shopwise is a **quality-driven commerce application** created as a **QA/SDET showcase project** and evolving toward a **marketable e-commerce starter kit**.

It is intentionally designed to demonstrate more than basic CRUD or UI assembly.
The project aims to show how a modern commerce system can be:

- architected cleanly
- tested deeply
- documented explicitly
- evolved safely through decisions and feedback

Shopwise is not positioned as a full enterprise commerce platform.
It is positioned as a **serious engineering-grade foundation** for a small-to-medium e-commerce product.

---

## 2. Why Shopwise Exists

The project exists for two connected reasons:

### 2.1 QA/SDET showcase

Shopwise demonstrates practical capabilities in:

- backend testing
- API testing
- browser E2E testing
- concurrency verification
- architecture review
- decision tracking through ADRs
- documentation-driven engineering

### 2.2 Product direction

The project is also evolving beyond a pure showcase into a **marketable starter kit direction**:
a well-structured commerce core that could realistically serve as the basis for a branded or custom e-commerce application.

This means the project must remain:

- technically credible
- commercially realistic
- maintainable
- extensible without premature overengineering

---

## 3. Product Direction

The current product direction is:

> **Minimal Marketable Product (MMP)**  
> rather than a bare MVP.

This means the goal is not merely to prove that “an e-shop can work”, but to provide a small, coherent, presentable product slice that feels realistic and usable.

Current direction emphasizes:

- realistic catalogue behavior
- guest and authenticated shopping flows
- checkout and order lifecycle correctness
- payment and shipping provider architecture
- deployment of a public demo
- quality and testability as part of product value

---

## 4. Who Shopwise Is For

### Primary audience (today)

- recruiters
- hiring managers
- engineering reviewers
- technical leads evaluating QA/SDET/architecture capability

### Future product audience (direction)

- small teams needing a commerce starter kit
- projects that want a clean backend/frontend foundation
- teams that value strong testing and architecture discipline
- white-label or custom-commerce experimentation around a stable core

---

## 5. What Problems It Tries to Solve

At product level, Shopwise focuses on the following problem space:

### Commerce correctness

A store must correctly handle:

- catalogue browsing
- cart lifecycle
- guest checkout
- orders and payment flow
- inventory reservation
- fulfillment/shipping flow
- order history and snapshot truth

### Low-friction buying experience

A realistic store should support:

- guest shopping
- low-friction checkout
- automatic and contextual promotion behavior
- account linking without unnecessary barriers
- SSR-capable customer-facing experience

### Safe system evolution

The project must support growth without chaos:

- architecture decisions are explicit
- critical invariants are guarded
- documentation and tests evolve with the code
- provider integrations are isolated behind clear boundaries

---

## 6. What Makes Shopwise Different

Shopwise intentionally differs from a typical portfolio demo in several ways:

- **testing is central**, not auxiliary
- **architecture decisions are documented**, not implied
- **runtime boundaries are explicit**, including async workers and external provider mocks
- **historical business truth is snapshot-based**
- **database-specific correctness is verified**, not assumed
- **frontend integration is treated as architectural feedback**, not just presentation

The project is designed to demonstrate quality thinking, not just feature completion.

---

## 7. Current Product Scope

The current product scope includes:

- product catalogue
- cart flows (guest + authenticated)
- checkout
- guest checkout
- guest order claiming after verified identity
- inventory reservation
- order lifecycle
- provider-agnostic payment architecture
- carrier-agnostic shipping architecture
- async email flows
- public multi-service demo deployment

Frontend work is focused on validating real integration and user-visible flows, not merely creating a visual shell.

---

## 8. Quality as Product Value

In Shopwise, quality is not a secondary engineering concern.
It is part of the product value proposition.

The product is intentionally designed so that the following are visible and demonstrable:

- determinism of business behavior
- traceability of decisions
- confidence provided by automated tests
- clarity of architecture
- ability to evolve without fragile rewrites

---

## 9. Non-Goals

The following are intentionally **not** current goals:

- building a full enterprise commerce suite
- supporting every possible promotion type immediately
- introducing full multi-tenancy now
- implementing every possible payment/carrier integration
- optimizing for extreme scale before the business model exists
- replacing dedicated ERP/WMS systems

Shopwise is meant to be strong and extensible, but not bloated.

---

## 10. Evolution Direction

The project is expected to continue evolving in these directions:

- richer pricing / VAT / promotions behavior
- stronger frontend integration guard
- more realistic commerce UX flows
- improved deployment and operability
- stronger auditability
- better-defined v1.0 scope as implementation findings stabilize

Architecture is intentionally allowed to evolve through implementation findings, provided such evolution is captured explicitly in ADRs and reflected in the current baseline.

---

## 11. Relationship to Documentation

This vision document explains **why the product exists and where it is going**.

For other perspectives, see:

- **Current Architecture Baseline** — what is true now
- **ADR Index** — why major decisions were made
- **Test Strategy** — how quality is validated
- **Onboarding** — how to navigate the project
