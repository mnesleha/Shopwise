# Guest Order Flow

## Purpose

This scenario demonstrates a complete guest checkout flow in the public Shopwise demo.

It is designed to show how an anonymous customer can browse the storefront, add products to cart, complete checkout without registering an account, and access the resulting order through an email-driven guest order link.

---

## What this scenario demonstrates

- public storefront access
- product filtering
- cart composition with products using different VAT classes
- checkout with **Cash on Delivery**
- guest order access through **Mailpit**
- guest order detail with discounts and VAT breakdown

---

## Video preview

<video src="https://github.com/user-attachments/assets/16b08932-c63b-4cad-8292-f4630ee88a62" controls width="100%"></video>

---

## Accounts used

This is a **guest flow**.

No authenticated customer account is required.

---

## Step-by-step walkthrough

1. Open the public storefront and navigate to the product catalog.
2. Use the filter panel to narrow down the visible product list.
3. Add one product with **21% VAT** to the cart.
4. Add another product with a different VAT class to the cart.
5. Open the cart detail page.
6. Review cart contents, pricing, discounts, and VAT breakdown.
7. Continue to checkout.
8. Fill in the checkout form as a **new guest customer**.
9. Select:
   - **Payment method:** Cash on Delivery
   - **Shipment method:** Standard
10. Submit the order using the guest checkout path.
11. Open **Mailpit** and locate the guest order email.
12. Open the guest order link from the email.
13. Review the guest order detail page.

---

## Expected result

After completing this scenario:

- the order is successfully created without account registration,
- the guest order email is delivered to Mailpit,
- the guest order link opens correctly,
- the order detail is accessible,
- discounts are visible where applicable,
- and VAT breakdown is visible on the final order detail.
