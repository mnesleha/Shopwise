# Cart Merge

## Purpose

This scenario demonstrates how Shopwise handles cart continuity across authenticated and anonymous sessions.

It is designed to show that an authenticated customer cart and a guest cart can be created separately and then merged correctly after the customer logs in again.

---

## What this scenario demonstrates

- authenticated cart state
- anonymous cart state
- session switching through logout and login
- merge behavior after authentication
- final merged cart visibility

---

## Video preview

<video src="https://github.com/user-attachments/assets/6e756c52-2248-4e5c-9392-27bb81a92ea2" controls width="100%"></video>

---

## Accounts used

This scenario uses an **existing seeded customer account**.

A guest cart is also created during the same scenario after logout.

---

## Step-by-step walkthrough

1. Log in with an existing seeded customer account.
2. Open the product catalogue.
3. Add a product to the authenticated cart.
4. Open the authenticated cart detail page.
5. Log out.
6. Return to the product catalogue as a guest user.
7. Add another product to the guest cart.
8. Log in again with the same customer account.
9. Observe the cart merge confirmation feedback.
10. Open the cart detail page.
11. Verify that the final cart contains items from both cart states.

---

## Expected result

After completing this scenario:

- the authenticated cart is created successfully,
- the guest cart is created independently after logout,
- logging back in triggers cart merge behavior,
- merge feedback is displayed,
- and the final cart contains the expected combined set of items.
