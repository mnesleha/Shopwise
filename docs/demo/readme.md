# Demo Scenarios

This section contains reproducible showcase scenarios for the public Shopwise demo environment.

Each scenario is designed to demonstrate a concrete part of the application in a way that is easy to replay, present, and verify. The scenarios are intentionally practical: they focus on visible business flows and user-facing behavior rather than internal implementation details.

Use these scenario pages as:

- a quick guide for manual walkthroughs,
- a companion to short demo videos,
- a reference for portfolio presentation and feature showcase.

## Available scenarios

### [Guest Order Flow](scenarios/Guest%20order%20flow.md)

A complete guest-order scenario showing the public storefront flow from product discovery to guest order access.

This scenario demonstrates:

- storefront browsing,
- filtering,
- adding products with different VAT classes to cart,
- checkout with **Cash on Delivery**,
- guest order access through **Mailpit**,
- and final guest order detail with discounts and VAT breakdown.

### [Auth Order Flow with Order History](scenarios/Auth%20order%20flow%20with%20order%20history.md)

An authenticated customer scenario focused on saved account data and post-order visibility.

This scenario demonstrates:

- login with an existing seeded customer account,
- profile and saved address management,
- cart and checkout flow with reused address data,
- card payment through **AcquireMock**,
- final order detail,
- and customer order history containing both seeded and newly created orders.

### [Cart Merge](scenarios/Cart%20merge.md)

A focused scenario showing how authenticated and anonymous cart states are merged after login.

This scenario demonstrates:

- authenticated cart creation,
- guest cart creation after logout,
- restoration of customer context after login,
- cart merge feedback,
- and final merged cart state.

### [Order Claim](scenarios/Order%20claim.md)

A guest-to-account scenario showing how a guest order can be assigned to an existing customer account after sign-in.

This scenario demonstrates:

- guest cart and guest checkout flow,
- guest order access through **Mailpit**,
- account-aware order detail behavior,
- sign-in-based order claiming,
- and claimed order visibility in customer order history.

### [Registration and Email Verification](scenarios/Registration%20and%20email%20verification.md)

A short authentication scenario showing self-service account creation and email verification.

This scenario demonstrates:

- transition from sign-in to registration,
- new customer account creation,
- verification flow through **Mailpit**,
- redirect into the authenticated customer area,
- and visible authenticated identity in the profile and header.

### [Backoffice Shipment Processing](scenarios/Backoffice%20shipment%20processing.md)

A cross-role scenario showing how shipment lifecycle changes made in admin are reflected in the customer-facing order experience.

This scenario demonstrates:

- authenticated checkout and payment,
- automatic shipment creation after successful order flow,
- shipment visibility in customer order detail,
- backoffice shipment status updates in Django admin,
- and customer-facing tracking/history updates after shipment progress.

### [Backoffice Promotion and Offer](scenarios/Backoffice%20promotion%20and%20offer.md)

A cross-role scenario showing how a backoffice campaign action leads to a customer-facing offer flow and visible cart discount.

This scenario demonstrates:

- authenticated storefront context,
- campaign creation and sending through the admin promotions workflow,
- offer delivery through **Mailpit**,
- customer-side promotion claim flow,
- visible discount application in cart,
- and resulting offer state visible in admin.
