# ADR-0XX: Handling Next.js Router Cache Race Conditions for User-Specific Header Data

**Status**: Accepted

**Date**: Sprint 11

**Decision type**: Architecture

## Context

During Sprint 11 (FE MVP used as a Backend Guard), we refactored the application header to leverage Next.js App Router Server Components (SSR) for better performance, SEO, and cookie-based auth forwarding.

However, the header contains **highly user-specific and frequently changing data**:

- Authentication state (logged-in vs anonymous, user email)
- Cart badge count (guest cart and authenticated cart)

Initially, we attempted to keep these values SSR-driven by calling:

- `router.refresh()` after mutations (login/logout/cart changes)
- followed by navigation (`router.push()`)

We observed flakiness where the header state updated only after a full page reload or updated inconsistently across fast navigations.

### Root cause

In Next.js App Router, `router.refresh()` is **fire-and-forget** (returns void and cannot be awaited). When `router.push()` occurs immediately after, a **race condition** can occur between:

- revalidation of server-rendered segments/layouts
- router cache serving previously rendered layouts from memory

As a result:

- Layout/header SSR may be served from Router Cache even after `router.refresh()` was triggered.
- User-specific header values can remain stale until a hard refresh.

This issue becomes more visible in e-commerce flows (add-to-cart → navigate quickly → header still shows old cart count).

## Decision

Adopt a **hybrid SSR/CSR header** approach:

- Keep the header layout/structure SSR (logo/navigation links/static elements).
- Move user-specific, frequently updated parts into **Client Components**:
  - Auth status widget (logged-in vs logged-out, email display)
  - Cart badge widget (item count)

The CSR widgets update in-place using client-side state and/or lightweight API calls, without depending on SSR re-render or router cache invalidation.

## Implementation Notes

- SSR header remains responsible for stable navigation structure.
- Auth and cart widgets are implemented as isolated client components (“leaf components”).
- After login/logout/cart mutations, the UI updates via client-side state updates.
  - If an API confirmation is needed, widgets can re-fetch their own data.
- Avoid using `router.refresh()` as a primary mechanism to update user-specific header UI.

## Consequences

**Positive**

- Eliminates race conditions caused by Next.js Router Cache during fast navigations.
- Improves perceived responsiveness (cart badge and auth state update immediately).
- Reduces reliance on SSR re-rendering for micro-updates.

**Negative / Trade-offs**

- Introduces CSR/hydration boundaries inside the header.
- Potential for minor UI “pop-in” if widget initial state differs from server-rendered markup.
- Requires explicit client-side data consistency strategy (revalidation after mutations).

## Alternatives Considered

1. **Keep header fully SSR and use `router.refresh()`**
   - Rejected due to non-deterministic behavior and race conditions with navigation and router cache.

2. **Force full page reload after key actions**
   - Rejected as poor UX and defeats SSR/SPA benefits.

3. **Introduce TanStack Query immediately**
   - Postponed. While TanStack Query would provide robust client-side caching, invalidation, deduplication, and stale-while-revalidate semantics, it also adds a significant abstraction layer.
   - In the FE Guard phase, we prefer the simplest possible client to identify backend contract gaps.
   - TanStack Query remains planned for a later “FE robustness/stabilization” sprint.

## Why TanStack Query Later

TanStack Query is a good long-term fit because:

- It provides a first-class client-side cache with explicit invalidation (`invalidateQueries(['cart'])`).
- It reduces manual re-fetch orchestration and avoids router cache concerns entirely for client widgets.
- It improves consistency across multiple components that depend on the same data (cart badge, cart page, checkout summary).

We will adopt it once:

- backend contract stabilizes (findings resolved)
- FE MVP flows are complete (order history, cancellation, cart merge)
- we can add/maintain a stable test safety net (Playwright E2E + selective RTL/Vitest tests)

## Testing Guidance

- Prefer Playwright E2E tests for end-to-end correctness across navigation and caching behaviors:
  - add-to-cart → navigate quickly → badge updates correctly
  - login/logout → auth widget updates without hard refresh
- Add RTL/Vitest tests selectively for widget behavior and error handling (avoid coupling tests to internal caching implementation).

## Related ADRs / Docs

- [ADR-030](./ADR-030-JWT-in-httpOnly-Cookies-with-SSR-Forwarding-Strategy.md): JWT in httpOnly cookies with SSR forwarding strategy (authentication baseline)
- Sprint 11 handover: FE MVP as Backend Guard (findings-driven development)
