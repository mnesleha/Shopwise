# Demo Seed Reference

This document describes the current deterministic demo seed created by `python manage.py seed_data --profile=demo`.

## Scope

The demo profile currently seeds:

- four explicit demo users
- three tax classes
- one active supplier with address and payment details
- three top-level categories
- fifteen showcase products with explicit slugs, prices, stock, and descriptions
- product media from `backend/utils/seed/assets/products/`
- two line-level promotions
- one auto-applied order promotion
- one campaign-linked offer token

It intentionally does not seed order history, fulfillment scenarios, or narrative customer journeys yet.

## Seeded Users

| Role     | Email                        | Password           |
| -------- | ---------------------------- | ------------------ |
| Admin    | `admin@shopwise.test`        | `DemoAdmin123!`    |
| Staff    | `staff@shopwise.test`        | `DemoStaff123!`    |
| Customer | `alice.walker@shopwise.test` | `DemoCustomer123!` |
| Customer | `martin.novak@shopwise.test` | `DemoCustomer123!` |

## Catalogue Summary

Categories:

- Electronics
- Grocery
- Pets

Products are defined explicitly in `backend/utils/seed/demo/config.py` and keep stable slugs for URLs, media folders, and automated tests.

## Commercial Layer

### Line Promotions

1. `Electronics Discount`
   - code: `demo-electronics-discount`
   - type: `PERCENT`
   - value: `10.00`
   - targets: category `Electronics`
   - priority: `20`

2. `Selected Products 15% Off`
   - code: `demo-selected-products-15-off`
   - type: `PERCENT`
   - value: `15.00`
   - targets: `wireless-headphones`, `usb-c-dock`, `portable-ssd`
   - priority: `30`

Because the selected-products promotion has higher priority, it wins over the category-level electronics promotion for those three SKUs.

### Order Promotion

1. `Demo Order Discount`
   - code: `demo-order-discount`
   - acquisition mode: `AUTO_APPLY`
   - type: `FIXED`
   - value: `250.00`
   - minimum order value: `3500.00`
   - stacking policy: `STACKABLE_WITH_LINE`

This promotion is intended for threshold-order demos after line promotions have already been resolved.

### Campaign Offer

The current domain models campaign offers as an `OrderPromotion` plus a linked `Offer` token.

- Promotion name: `Campaign Welcome Offer`
- promotion code: `campaign-welcome-offer`
- acquisition mode: `CAMPAIGN_APPLY`
- type: `FIXED`
- value: `300.00`
- minimum order value: `1500.00`
- offer token: `DEMO-WELCOME-2025`
- offer status: `DELIVERED`

## Reset Behavior

`python manage.py seed_data --profile=demo --reset` performs a clean rebuild of the demo dataset.

Reset includes:

- carts, orders, order items, and payments
- products, categories, supplier records, and tax classes
- line promotions, order promotions, and offers
- demo product media cleanup scoped to the seeded demo product slugs

The command is intended to be rerun safely and should converge back to the same deterministic state.

## Media Convention

Product media is resolved from slug-based folders under `backend/utils/seed/assets/products/`.

Example:

```text
backend/utils/seed/assets/products/
wireless-headphones/
  wireless-headphones-1.jpg
  wireless-headphones-2.jpg
portable-ssd/
  portable-ssd-1.jpg
```

Files are sorted by filename. The first file becomes `primary_image` and the remainder become gallery images.
