# Order Claim

## Purpose

This scenario demonstrates how Shopwise handles guest orders that are later assigned to an existing customer account.

It is designed to show how an anonymous customer can place a guest order, open the order through an email link, sign in with an existing account that uses the same email address, and then see the order appear in authenticated order history.

---

## What this scenario demonstrates

- guest cart and guest checkout flow
- order creation without prior sign-in
- guest order access through Mailpit
- account-aware behavior on guest order detail
- sign-in-based order claiming
- claimed order visibility in authenticated order history

---

## Video preview

<video src="https://github.com/user-attachments/assets/ac50e3e0-8370-4e4c-af45-8f364b8da689" controls width="100%"></video>

---

## Accounts used

This scenario starts as a **guest flow**.

Later in the flow, it uses an **existing seeded customer account** with the same email address as the guest order.

---

## Step-by-step walkthrough

1. Open the product catalogue as a guest user.
2. Add a product to the cart.
3. Open the cart detail page.
4. Continue to checkout.
5. Complete checkout as a guest customer using **Cash on Delivery**.
6. Open **Mailpit** and locate the guest order email.
7. Open the guest order link from the email.
8. On the guest order detail page, observe the message indicating that an account already exists for the same email address.
9. Use the sign-in action from the order detail page.
10. Log in with the existing customer account.
11. Observe the order-claim confirmation toast.
12. Open the authenticated order history.
13. Verify that the claimed order now appears in the customer account.

---

## Expected result

After completing this scenario:

- the guest order is created successfully,
- the guest order link is delivered through Mailpit,
- the guest order detail recognizes the existing account tied to the same email address,
- the customer can sign in and claim the order,
- the claim confirmation is shown,
- and the claimed order becomes visible in authenticated order history.
