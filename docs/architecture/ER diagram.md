# Entity Relationship Diagram – Shopwise

This document describes the data model of the Shopwise system,
including entities, their attributes, and relationships.

The data model represents the source of truth
for backend implementation and database design.

version 1.0 - proposal

## Domain Overview

The Shopwise data model covers the following domains:

- User management
- Product catalog
- Categories
- Discounts
- Orders
- Payments

## User

Represents a registered user of the system.

Field Type Description
id UUID Primary key
email String Unique identifier
password String Hashed
is_staff Boolean Admin flag
created_at DateTime Creation timestamp

## Category

Represents a hierarchical product category.

Field Type Description
id UUID Primary key
name String Category name
parent_id UUID Self-reference
is_active Boolean Visibility flag

Relationships:
Category → Category (parent-child)
Category → Product (1:N)

## Product

Represents a sellable product.

Field Type Description
id UUID Primary key
name String Product name
description Text Description
price Decimal Base price
stock_quantity Integer Inventory
category_id UUID FK to Category
is_active Boolean Availability
created_at DateTime Creation timestamp

Relationships:
Product → Category (N:1)
Product → OrderItem (1:N)
Product → Discount (1:N)

## Discount

Represents a discount applied to products or categories.

Field Type Description
id UUID Primary key
name String Discount name
type Enum PERCENT / FIXED
value Decimal Discount value
valid_from DateTime Start
valid_to DateTime End
applies_to Enum PRODUCT / CATEGORY
product_id UUID Optional FK
category_id UUID Optional FK
is_active Boolean Enabled

Rules:

- Discount applies to either product or category, not both
- Only active discounts within valid date range are applied

## Order

Represents a customer order.

Field Type Description
id UUID Primary key
user_id UUID FK to User
status Enum CREATED, PAID, SHIPPED, DELIVERED, CANCELED
total_price Decimal Calculated
created_at DateTime Creation timestamp

Relationships:
Order → User (N:1)
Order → OrderItem (1:N)
Order → Payment (1:1)

## OrderItem

Represents an item within an order.

Field Type Description
id UUID Primary key
order_id UUID FK to Order
product_id UUID FK to Product
quantity Integer Ordered quantity
price_at_order_time Decimal Snapshot price
discount_applied Decimal Discount amount

## Payment

Represents a payment attempt for an order.

Field Type Description
id UUID Primary key
order_id UUID FK to Order
status Enum PENDING, SUCCESS, FAILED
created_at DateTime Timestamp

## Entity relationships summary

User 1 ──── N Order
Order 1 ──── N OrderItem
Order 1 ──── 1 Payment
Category 1 ──── N Product
Category 1 ──── N Discount
Product 1 ──── N OrderItem
Product 1 ──── N Discount

## Data Integrity Rules

- Referential integrity enforced via foreign keys
- Enum values validated at application level
- Business rules enforced in service layer

## Implementation Notes

- UUIDs used as primary keys
- Monetary values stored as Decimal
- Soft deletes handled via is_active flags

## Next Steps

- Create visual ER diagram
- Map entities to Django models
- Implement migrations
