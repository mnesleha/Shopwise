# Auth Order Flow with Order History

## Purpose

This scenario demonstrates an authenticated customer purchase flow in the public Shopwise demo.

It is designed to show how an existing customer can log in, manage saved address data, place a card-paid order, and then view the resulting order in the context of existing order history.

---

## What this scenario demonstrates

- authenticated customer experience
- profile and saved address management
- cart composition and checkout
- checkout using saved customer address data
- card payment through **AcquireMock**
- authenticated order detail
- order history with both seeded and newly created orders

---

## Video preview

> Video preview placeholder  
> Add the scenario video link or embedded preview here once the media hosting approach is finalized.

---

## Accounts used

This scenario uses an **existing seeded customer account**.

Use the customer account documented in the demo seed reference.

---

## Step-by-step walkthrough

1. Log in with an existing seeded customer account.
2. Open the user profile.
3. Navigate to the saved addresses section.
4. Create or update a saved address.
5. Open the product catalogue.
6. Add products to the cart.
7. Open the cart detail page.
8. Review pricing, promotions, and VAT breakdown.
9. Continue to checkout.
10. Select the previously saved address during checkout.
11. Choose **card payment**.
12. Complete the payment through **AcquireMock**.
13. Open the resulting order detail page.
14. Navigate to the customer order history.
15. Verify that the new order appears alongside the seeded order history.

---

## Expected result

After completing this scenario:

- the customer can log in successfully,
- saved address data can be managed and reused,
- the order is successfully created through the authenticated checkout path,
- payment is completed through AcquireMock,
- the order detail is accessible immediately after checkout,
- and the order history contains both seeded historical orders and the newly created order.
