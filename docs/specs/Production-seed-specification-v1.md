# Shopwise Production Seed Specification v1

## Purpose

The production/demo seed must create a stable, visually representative, and functionally complete showcase state of the application.

It is intended for:

- public portfolio / CV showcase,
- guided video scenarios,
- repeatable reset/reseed workflows,
- recruiter and technical review,
- demonstration of quality-driven product and system design.

It is **not** intended primarily for:

- developer convenience,
- large volumes of test data,
- random or exploratory data generation,
- heavily configurable generic seed infrastructure.

The production seed must be:

- deterministic,
- explicit,
- readable,
- safely resettable,
- oriented toward showcase value rather than maximum flexibility.

---

## Design Principles

### 1. The production seed is separate from the dev seed

The production/demo seed must be treated as a distinct scenario/profile/command and must not inherit the assumptions of the current dev-oriented seed design if those assumptions do not serve the showcase use case.

### 2. The production seed is explicit

Catalog, users, promotions, offers, and showcase-ready entities should be defined explicitly in Python code rather than hidden behind a generic YAML-driven configuration layer, unless that layer provides clear practical value.

### 3. The production seed is presentation-oriented

Every seeded entity must exist for a clear reason:

- it supports a public demo flow,
- it supports a quality showcase,
- it supports a video scenario,
- it supports visual/product representativeness,
- or it is required for operational consistency of the demo.

### 4. The production seed does not pre-consume interactive scenarios

The seed must not create partially consumed or already-spent states for scenarios such as:

- cart merge,
- guest-to-auth transitions,
- order claiming,
- or similar flows that are meant to be performed live in a demo or test scenario.

The seed prepares the **conditions** for those scenarios, not the already-mutated end state.

### 5. Media assets are part of the repository

Seeded showcase product images are versioned in the repository and uploaded through Django storage during the seed process.

The seed must not hardcode public object-storage URLs into the database.

---

## Seeded Entities and Minimum Scope

## Users

The production seed must create the following identities.

### Superuser

Purpose:

- system administration,
- internal inspection,
- admin maintenance/debug.

Requirements:

- email
- password
- first name
- last name
- `is_superuser=True`
- `is_staff=True`

### Staff user

Purpose:

- admin/business showcase scenarios,
- safer demo alternative to the superuser account.

Requirements:

- email
- password
- first name
- last name
- `is_staff=True`
- not a superuser

### Customer user 1

Purpose:

- authenticated checkout,
- orders list / order detail,
- campaign / offer scenarios,
- cart merge scenarios

Requirements:

- email
- password
- first name
- last name

### Customer user 2

Purpose:

- alternative authenticated scenarios,
- separation of demo/test customer flows,
- optional campaign / email / claim-related scenarios

Requirements:

- email
- password
- first name
- last name

### General user requirements

All seeded identities must feel human and presentable. They must not be limited to email/password only.

---

## Tax Classes

The production seed must create exactly 3 tax classes:

- VAT 21%
- VAT 12%
- VAT 0%

Purpose:

- VAT breakdown demonstration,
- product category variation,
- realistic pricing and summary logic.

---

## Supplier

The production seed must create **one active default supplier** that is fully valid for the checkout and order pipeline.

### Supplier

Requirements:

- active
- valid for order creation
- valid for pricing and supplier snapshot/config resolution
- usable without manual post-seed repair

### Supplier Addresses

The supplier must include all default addresses required by the domain model, at minimum:

- default billing address
- default shipping / operational address if required by the application rules

### Supplier Payment Details

The supplier must include all payment details required by the application so that:

- supplier configuration validation passes,
- checkout does not fail on supplier configuration,
- order summary works,
- cart summary works,
- order/payment orchestration can proceed.

### Supplier Configuration

The seed must explicitly ensure that supplier-related configuration is complete enough to avoid runtime checkout failure.

This is a hard requirement of the production seed.

---

## Categories

The production seed must create 3 categories:

- Electronics
- Grocery
- Pets

Requirements:

- active
- usable in the storefront
- linked to products
- usable in promotion logic

---

## Products

The production seed must create **15 showcase products**.

### Electronics

1. Wireless Headphones
2. Mechanical Keyboard
3. USB-C Dock
4. Smart Speaker
5. Portable SSD

### Grocery

6. Organic Pasta
7. Olive Oil
8. Granola Mix
9. Green Tea
10. Dark Chocolate

### Pets

11. Dog Food Premium
12. Cat Litter Pro
13. Pet Shampoo
14. Chew Toy Rope
15. Pet Bowl Set

### Product Requirements

Each seeded product must have at minimum:

- name
- slug
- category
- tax class
- active/published state suitable for the storefront
- valid price
- in-stock / inventory-ready state
- valid supplier relation/configuration if required by the domain
- at least 1 main image

### Gallery Images

A selected subset of products must have multiple images for a stronger product-detail demo.

Recommended:

- Wireless Headphones → 3 images
- Mechanical Keyboard → 3 images
- Smart Speaker → 2 images
- Organic Pasta → 2 images
- Dog Food Premium → 2 images

All other products may have only 1 main image in v1.

### Stable Product Identity

Each product must have a stable **slug** that serves as:

- the seed identifier,
- the mapping key for the image catalogue,
- the stable identifier for tests,
- the stable identifier for demo/video scenarios.

Recommended slugs:

- `wireless-headphones`
- `mechanical-keyboard`
- `usb-c-dock`
- `smart-speaker`
- `portable-ssd`
- `organic-pasta`
- `olive-oil`
- `granola-mix`
- `green-tea`
- `dark-chocolate`
- `dog-food-premium`
- `cat-litter-pro`
- `pet-shampoo`
- `chew-toy-rope`
- `pet-bowl-set`

---

## Prices

Every seeded product must have a valid price.

Requirements:

- prices must be realistic enough for presentation,
- prices must be sufficiently varied,
- pricing must support:
  - cart summary,
  - order summary,
  - VAT breakdown,
  - promotion scenarios,
  - minimum-order-value promotion logic.

The seed must ensure that pricing data is complete and internally consistent.

---

## Inventory / Stock

All showcase products must be in stock by default.

Requirements:

- no seeded showcase product is out of stock unless intentionally introduced as a later specialized test/demo case,
- seeded catalog must be safe for live demo usage without accidental stock-related blockers.
- one dedicated out-of-stock product for a targeted scenario

---

## Product Images / Media

The production seed must support image upload through the active Django storage backend.

### Requirements

- images are versioned in the repository,
- the seed uploads them through model/file/image fields,
- the seed does not write final public storage URLs directly into the database,
- the active storage backend decides where the files are stored,
- the same seed works with local storage and production object storage.

### Recommended Asset Structure

```text
backend/utils/seed/assets/products/
  wireless-headphones/
    main.jpg
    gallery-1.jpg
    gallery-2.jpg
  mechanical-keyboard/
    main.jpg
    gallery-1.jpg
    gallery-2.jpg
  ...
```

### Mapping Rule

Products map to asset folders by slug.

---

## Order Promotion

The production seed must create at least one order-level promotion.

Requirements:

- auto-apply
- minimum order value
- visible in cart and/or checkout behavior

Purpose:

- demonstrate promotion logic,
- support business realism,
- enrich cart/checkout showcase behavior.

---

## Promotions

The production seed must create at least two promotions.

### Promotion A

- fixed discount
- applied to one category

Recommended category:

- Electronics

### Promotion B

- percentage discount
- applied to several specific products

Recommended products:

- Smart Speaker
- Green Tea
- Pet Shampoo

Purpose:

- demonstrate category-scoped and product-scoped promotion logic.

---

## Offer

The production seed must create one offer for the campaign demo.

Requirements:

- usable in a customer-facing flow
- tied to an email/campaign-oriented use case
- deterministically configured

---

## Campaign-Ready State

The seed does not need to execute a campaign automatically, but it must create all conditions required to run the campaign scenario.

That means:

- an existing offer,
- at least one suitable target customer,
- email-ready conditions,
- products/promotion context that makes the offer visible and meaningful.

---

## Orders / Carts / Scenario State

### What the seed must prepare

The seed must prepare:

- users,
- catalog,
- supplier configuration,
- promotions,
- offers,
- checkout-ready configuration,
- email/payment-ready environment assumptions.

### Orders

For one seeded customer, create:

- 1 delivered order
  - with correct shipment in DELIVERED status
- 1 cancelled order
- 1 active order
  - in a status suitable for display in active bucket

**Requirements**

- order items must be consistent with current catalog
- prices/taxes/order totals must match seeded configuration
- payment/shipment status must not be just “hard fake” if it violates domain rules
- active/completed grouping must work in UI without manual intervention

### What the seed must not pre-consume

The seed must **not** create already-spent scenario states such as:

- pre-consumed cart merge state,
- already-claimed order scenario state,
- other one-time mutated flows that stop being reproducible after one pass.

Those scenarios must be replayed as actions in a demo/test/video flow, not stored as a partially completed seeded state.

---

## Supported Showcase Scenarios

The production seed must support at minimum the following scenarios.

### 1. Guest checkout flow

It must be possible to:

- browse the catalog,
- add products to cart,
- view cart summary,
- complete checkout,
- go through the AcquireMock payment flow,
- observe related email flow in Mailpit.

### 2. Authenticated checkout flow

It must be possible to:

- log in as an existing seeded customer,
- shop and checkout,
- complete an order,
- view order list and/or order detail.

### 3. Cart merge scenario

The seed must prepare the conditions for this scenario:

- an existing authenticated user,
- a functioning catalog,
- working session/auth logic.

The scenario itself should be played live, for example:

- login → authenticated cart
- logout
- guest cart
- login
- merge

The merge is a scenario action, not a pre-seeded consumed state.

### 4. Promotion / offer / campaign flow

It must be possible to:

- trigger or demonstrate an offer/campaign-related flow,
- receive email in Mailpit,
- observe customer-facing pricing/promotion effect.

### 5. Admin inspection scenario

It must be possible to:

- log in to admin,
- inspect seeded products,
- inspect prices,
- inspect supplier configuration,
- inspect promotions/offers,
- inspect order/payment-related entities as part of the showcase.

---

## Out of Scope for Production Seed v1

The first version of the production seed does **not** need to handle:

- claim scenarios as pre-seeded ready-made states,
- bulk products,
- multiple suppliers,
- advanced shipping scenarios,
- large order history datasets,
- large campaign variation sets,
- complex out-of-stock scenarios,
- generic flexible seed configuration for arbitrary future use cases.

These may be added later, but they are not required for a strong first showcase-ready seed.

---

## Implementation Principles

### 1. The seed must be modular

Implementation must be split into logical parts, for example:

- users
- reference data
- supplier
- categories
- products
- prices
- images
- promotions
- offers
- scenario support

### 2. The seed must be implementable in phases

The refactor must be executed in logical phases. It should not be attempted as one giant rewrite without boundaries.

### 3. The seed must be readable

Seed data should be easy to understand and audit. Explicitness is preferred over over-abstraction.

### 4. The seed must be safely resettable

After a database reset, the production seed must be able to restore the application into a fully showcase-ready state.

---

## Recommended Implementation Phases

### Phase 1 — Reference Data and Identities

- users
- tax classes
- supplier
- supplier addresses
- supplier payment details
- categories

### Phase 2 — Catalog Core

- products
- slugs
- prices
- stock
- category/tax assignment

### Phase 3 — Product Media

- image catalogue integration
- upload via Django storage
- gallery support

### Phase 4 — Commercial Layer

- order promotion
- category/product promotions
- offer

### Phase 5 — Scenario Hardening

- verify guest checkout
- verify authenticated checkout
- verify cart merge preconditions
- verify campaign/email flow
- fill any missing configuration dependencies

---

## Expected Result

After a database reset followed by the production/demo seed, the application must be in a state where:

- the storefront looks representative,
- products have working images,
- cart summary works,
- VAT breakdown works,
- checkout works,
- supplier configuration is complete,
- promotions and offer exist,
- auth flow works,
- AcquireMock flow works,
- Mailpit-related flow is ready,
- admin contains coherent showcase data.

This is the accepted target state of the production seed v1.
