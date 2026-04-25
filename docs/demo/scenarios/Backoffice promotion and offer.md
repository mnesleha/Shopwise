# Backoffice Promotion and Offer

## Purpose

This scenario demonstrates how Shopwise connects backoffice campaign actions with customer-facing promotion behavior.

It is designed to show how an authenticated customer can prepare a cart, how an admin can trigger a campaign through the promotions workflow, how the customer receives the offer through Mailpit, and how the claimed discount becomes visible in the cart.

---

## What this scenario demonstrates

- authenticated storefront context
- cart preparation before offer application
- campaign trigger in Django admin
- offer delivery through Mailpit
- customer-side promotion claim flow
- discount visibility in cart
- backoffice visibility of the resulting offer state

---

## Video preview

<video src="https://github.com/user-attachments/assets/2adcc56a-396a-4345-aa13-96938dabf2e1" controls width="100%"></video>

---

## Accounts used

This scenario uses:

- an **existing seeded customer account** for the storefront flow
- an **admin/staff account** for the backoffice campaign action

---

## Step-by-step walkthrough

1. Log in with an existing seeded customer account.
2. Open the product catalogue.
3. Add a product to the cart.
4. Keep the cart prepared for the later offer application.
5. Sign in to Django admin with the admin/staff account.
6. Open the promotions workflow used for campaign sending.
7. Create and send the campaign from the backoffice flow.
8. Open **Mailpit** and locate the campaign offer email.
9. Open the offer link from the email.
10. Review the promotion claimed screen.
11. Return to the customer cart detail page.
12. Verify that the claimed discount is now applied in the cart.
13. Return to Django admin.
14. Open the created offer detail and inspect the resulting backoffice state.

---

## Expected result

After completing this scenario:

- the customer has a prepared cart before the campaign is sent,
- the admin can trigger a campaign from the promotions workflow,
- the campaign email is delivered through Mailpit,
- the offer link opens correctly,
- the promotion is successfully claimed,
- the discount becomes visible in the customer cart,
- and the resulting offer state is visible in admin.
