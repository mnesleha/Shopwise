# Domain Model

## Purpose of This Document

This document describes the **core domain model of the Shopwise system**.

Its goal is to explain:

- which business concepts exist in the system
- how responsibilities are divided between domain entities
- how these entities relate to each other conceptually

This document focuses on **business meaning and boundaries**, not on database schemas or implementation details.

## Domain Modeling Principles

The Shopwise domain model is based on the following principles:

- Explicit separation of intent and result  
  User intent is represented by Cart, while business results are represented by Order.

- Workflow-oriented modeling  
  Entities are designed to support realistic business workflows rather than generic CRUD operations.

- Immutability where appropriate  
  Once created, Orders are treated as immutable results of a completed process.

- Simplicity over completeness  
  The model intentionally avoids unnecessary complexity while preserving realistic boundaries.

## Core Domain Entities

The core domain entities in Shopwise are:

- Product
- Category
- Cart
- CartItem
- Order
- Payment

## Product

Product represents an item that can be offered for sale.

Responsibilities:

- holds product attributes such as name, price, and availability
- serves as a reference for cart and order items

Products are treated as relatively stable entities and are not modified as part of checkout or payment workflows.

## Category

Category is used to organize products into a hierarchical structure.

Responsibilities:

- groups products for browsing and classification
- supports parent–child relationships

Categories are not involved in transactional workflows and serve purely as a structural concept.

## Cart

Cart represents **user intent to purchase**.

Responsibilities:

- collects items the user intends to buy
- enforces rules around item quantities and validity
- acts as the entry point for the checkout process

Key characteristics:

- a user can have at most one ACTIVE cart
- cart lifecycle is explicit and finite
- cart contents can be freely modified while the cart is ACTIVE

Cart exists to capture intent, not to represent a finalized trasaction.

## CartItem

CartItem represents a product selected by the user within a cart.

Responsibilities:

- links a product to a cart
- stores selected quantity
- validates business rules (e.g. quantity must be greater than zero)

CartItem has no meaning outside the context of a Cart.

## Order

Order represents the **result of a completed checkout**.

Responsibilities:

- captures a snapshot of purchased items
- stores calculated totals
- reflects the outcome of the checkout process

Key characteristics:

- Orders are created exclusively via Cart checkout
- Orders are treated as read-only from the API perspective
- Orders are immutable representations of a past business decision

Order deliberately does not allow modification of items after creation.

## Payment

Payment represents the outcome of an attempt to pay for an order.

Responsibilities:

- records payment result for an order
- drives order state transitions related to payment

Key characteristics:

- one-to-one relationship with Order
- payment is an explicit action
- payment outcome influences order status but does not modify order content

## Relationships Between Entities

Conceptually, the domain relationships are:

- Category → Product (classification)
- Cart → CartItem → Product (user intent)
- Order → OrderItem → Product (transaction result)
- Order → Payment (transaction outcome)

These relationships are designed to reflect real-world e-commerce workflows while keeping responsibilities clearly separated.

## Domain Boundaries and Responsibilities

A key goal of the domain model is to prevent responsibility leakage:

- Cart does not handle payments
- Order does not handle item modification
- Payment does not handle cart logic
- Category does not affect transactional behavior

## Summary

The Shopwise domain model is designed to be:

- explicit
- workflow-oriented
- easy to reason about
- well-aligned with testing and documentation needs

It provides a stable foundation for API design, testing strategy, and future frontend development.
