# Registration and Email Verification

## Purpose

This scenario demonstrates the public account registration flow in the Shopwise demo.

It is designed to show how a new customer can create an account, verify the email address through Mailpit, and enter the authenticated customer area with visible account identity in the UI.

---

## What this scenario demonstrates

- public authentication entrypoint
- self-service customer registration
- email verification flow
- Mailpit-based verification access
- redirect into authenticated customer area
- visible authenticated identity in profile and header

---

## Video preview

<video src="https://github.com/user-attachments/assets/0aa8daf4-0c96-4d7b-bfb3-99e21acd0cfb" controls width="100%"></video>

---

## Accounts used

This scenario creates a **new customer account** during the flow.

No seeded customer account is required.

---

## Step-by-step walkthrough

1. Open the public login page.
2. Use the registration link to switch to the sign-up flow.
3. Fill in the registration form for a new customer account.
4. Submit the registration form.
5. Observe the email verification feedback in the UI.
6. Open **Mailpit** and locate the verification email.
7. Open the verification link from the email.
8. Observe the redirect into the authenticated customer area.
9. Open the profile view if needed.
10. Verify that the new customer identity is visible in the profile and in the storefront header.

---

## Expected result

After completing this scenario:

- a new customer account is created successfully,
- the verification email is delivered to Mailpit,
- the verification link activates the account,
- the customer is redirected into the authenticated area,
- and the authenticated identity is visible in both profile view and header state.
