# Backoffice Shipment Processing

## Purpose

This scenario demonstrates how shipment lifecycle management connects backoffice processing with the customer-facing order experience in the Shopwise demo.

It is designed to show how a normal authenticated checkout leads to shipment creation, how shipment state is updated in Django admin, and how those changes become visible in the customer-facing order detail and order history.

---

## What this scenario demonstrates

- authenticated checkout flow
- card payment through AcquireMock
- shipment creation after successful order flow
- customer-facing shipment tracking view
- shipment processing in Django admin
- lifecycle propagation from backoffice to customer UI
- delivered order visibility in completed order history

---

## Video preview

<video src="https://github.com/user-attachments/assets/70aaad7e-c46d-4291-9936-895faa9b4b4f" controls width="100%"></video>

---

## Accounts used

This scenario uses:

- an **existing seeded customer account** for the storefront flow
- an **admin/staff account** for shipment processing in Django admin

---

## Step-by-step walkthrough

1. Log in with an existing seeded customer account.
2. Open the product catalogue.
3. Add a product with **21% VAT** to the cart.
4. Open the cart detail page if needed.
5. Continue to checkout.
6. Complete checkout using **card payment**.
7. Finish the hosted payment flow through **AcquireMock**.
8. Open the newly created order detail page.
9. Review the order detail and confirm that shipment information is present.
10. Open the shipment tracking detail from the customer-facing order view.
11. Sign in to Django admin with the admin/staff account.
12. Locate the shipment belonging to the newly created order.
13. Change the shipment state to **In Transit**.
14. Return to the customer-facing order detail and refresh the page.
15. Confirm that the updated shipment state is now visible.
16. Return to Django admin.
17. Change the shipment state to **Delivered**.
18. Return to the customer-facing order detail and refresh again.
19. Confirm that the shipment is now shown as delivered.
20. Open order history and verify that the order appears in the delivered/completed section.

---

## Expected result

After completing this scenario:

- the customer can complete an authenticated card-paid checkout,
- a shipment is created for the new order,
- shipment tracking is visible in the customer-facing order detail,
- shipment status can be updated in Django admin,
- those updates are reflected in the customer UI after refresh,
- and the order appears in delivered/completed history once shipment processing is finished.
