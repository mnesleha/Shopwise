# ADR-031: Do Not Use `waitForResponse` for Proxied API Calls in Playwright E2E Tests

**Status**: Accepted

**Date**: Sprint 12

**Decision type**: Testing

**Related**: ADR-030 (JWT in httpOnly Cookies), ADR-016 (Postman CLI for API Testing),
frontend E2E test suite (`tests/e2e/`)

---

## Context

Shopwise uses Next.js with a rewrite rule that proxies all `/api/:path*` requests
to the Django backend:

```js
// next.config.js
async rewrites() {
  return [
    {
      source: "/api/:path*",
      destination: `${backendOrigin}/api/:path*/`,
    },
  ];
}
```

Playwright E2E tests exercise full user flows (login, add to cart, checkout) against
a running Next.js dev server (`http://localhost:3000`).

During development of the checkout E2E tests, `page.waitForResponse()` was used to
assert that specific backend API calls succeeded:

```ts
const checkoutResponse = page.waitForResponse(
  (r) =>
    r.url().includes("/api/v1/cart/checkout/") &&
    r.request().method() === "POST",
);
await submitCheckout(page);
const res = await checkoutResponse;
expect(res.ok()).toBeTruthy();
```

This pattern produced intermittently failing tests across browsers, with different
failure modes per browser:

- **WebKit**: `page.waitForResponse: Test timeout of 120000ms exceeded` — the
  response was never matched, even with a 120-second timeout.
- **Firefox**: `NS_BINDING_ABORTED` — a competing navigation aborted the in-flight
  request before the response could be captured.
- **Chromium**: passed consistently, masking the underlying issue.

The tests were non-deterministic. Identical test code would pass all three browsers
on one run and fail 1–2 browsers on the next.

---

## Root Cause Analysis

### 1. URL visible to Playwright depends on browser engine and timing

When Next.js proxies a request, the Playwright `response` object may expose:

- the **client-side URL** (e.g. `http://localhost:3000/api/v1/cart/checkout/`)
- the **backend URL** (e.g. `http://127.0.0.1:8000/api/v1/cart/checkout/`)
- an **internal Next.js URL** used during server-side routing

This is not consistent across Chromium, Firefox, and WebKit because each engine
implements the request lifecycle differently and Playwright captures responses at
different points in that lifecycle.

### 2. `waitForResponse` listener registration race

`page.waitForResponse()` registers a listener on the `response` event. If the
response arrives before the listener is registered — possible when the previous
`await` yields just as the network stack delivers the response — the event is
missed entirely. This is particularly common on fast machines or when the
network round-trip is short (localhost).

The correct pattern is to register `waitForResponse` **before** the action that
triggers the request. However, even with this ordering, the URL-matching predicate
can still fail to match due to issue #1.

### 3. Navigation conflicts on Firefox

After login, the application calls `router.push("/products")`. If the test also
calls `page.goto("/products")` immediately after, two concurrent navigation
requests are issued. Firefox aborts the first (application-initiated) navigation
with `NS_BINDING_ABORTED`. This is a separate but related symptom: `waitForResponse`
for the login endpoint was the mechanism that forced the test to wait in the right
place, and removing it without adding an explicit `waitForURL` call exposed the
underlying navigation race.

---

## Decision

**`page.waitForResponse()` must not be used to assert the outcome of API calls
that go through a Next.js proxy rewrite in Playwright E2E tests.**

### Rationale

The outcome of a business operation (login, checkout, add to cart) is fully
observable through the resulting UI state. Asserting that a specific network
response returned HTTP 200 is:

1. **Unreliable** — URL matching through a proxy rewrite is not stable across
   browser engines in Playwright.
2. **Redundant** — if the API call failed, the UI would not transition to the
   expected state, and the UI assertion would fail with a clearer message.
3. **Fragile** — it couples the test to transport-level details (URL format,
   HTTP status) rather than behavior (user reaches the order confirmation page).

### Approved pattern: assert on resulting UI state

Assert the outcome by verifying the URL and visible elements that only appear
after a successful server response:

```ts
// ✅ DO: assert on resulting navigation and UI
await submitCheckout(page);
await expect(page).toHaveURL(/\/orders\/\d+/, { timeout: 30_000 });
await expect(page.locator("[data-testid='order-title']")).toBeVisible();
await expect(page.locator("[data-testid='order-status']")).toBeVisible();
```

```ts
// ✅ DO: after login, wait for the app's own redirect before proceeding
await page.locator("[data-testid='login-submit']").click();
await page.waitForURL(/\/products/, { timeout: 15_000 });
```

```ts
// ❌ DO NOT: intercept proxied responses by URL pattern
const resp = page.waitForResponse(
  (r) => r.url().includes("/api/v1/cart/checkout/") && r.request().method() === "POST"
);
await submitCheckout(page);
const res = await resp;
expect(res.ok()).toBeTruthy(); // unreliable on WebKit and Firefox
```

### When `waitForResponse` is acceptable

`page.waitForResponse()` is acceptable only when:

- The request is made **directly to the test server** (no proxy rewrite), **and**
- The test is run **Chromium-only** and this is explicitly documented, **and**
- There is no observable UI change that can substitute for the assertion.

None of these conditions apply to Shopwise's checkout or auth flows.

### Navigation conflict rule

When the application performs a programmatic navigation after an async operation
(e.g. `router.push("/products")` after login), always use `page.waitForURL()`
to let that navigation settle before issuing any subsequent `page.goto()` or
navigation-triggering action:

```ts
// After clicking login submit:
await page.waitForURL(/\/products/, { timeout: 15_000 });
// Now safe to navigate elsewhere
await page.goto("/products");
```

---

## Consequences

**Positive**

- Tests are deterministic across Chromium, Firefox, and WebKit.
- Test failures produce clear messages about observable behavior, not internal
  network details.
- Tests are decoupled from URL structure of the proxy layer; renaming API paths
  does not require test updates.
- Simpler test code with fewer moving parts.

**Trade-offs**

- HTTP status codes are not explicitly asserted in E2E tests.
- A backend regression that returns a non-2xx status but somehow still renders
  the success UI would not be caught. This is an accepted trade-off: such scenarios
  are covered by backend unit tests and Postman contract tests (ADR-016), not by
  E2E UI tests.

**Unchanged**

- `waitForResponse` remains valid in Postman contract tests, which call the
  backend directly without a proxy layer.
- Backend unit tests (pytest) are the authoritative source for HTTP status
  assertions.

---

## Alternatives Considered

### Use `page.route()` to intercept and inspect requests

Rejected. `page.route()` can intercept requests before they are sent and inspect
or mock them. Using it to assert real backend behavior would require unmocking,
adding complexity. It is appropriate for unit-style component tests with a mocked
backend, not for live E2E flows.

### Run Playwright only on Chromium

Rejected. Chromium passing consistently masked the underlying reliability problem.
Running all three engines is required to surface cross-browser regressions and
ensures the application works for Safari users (WebKit) and Firefox users.

### Switch to a direct backend URL in tests (bypass Next.js proxy)

Rejected. E2E tests must exercise the full stack including the Next.js proxy,
authentication cookie handling, and SSR. Bypassing the proxy would not test what
users actually experience.

### Add retry logic around `waitForResponse`

Rejected. Retrying a fundamentally unreliable mechanism does not fix the root
cause. It would hide flakiness rather than eliminate it.
