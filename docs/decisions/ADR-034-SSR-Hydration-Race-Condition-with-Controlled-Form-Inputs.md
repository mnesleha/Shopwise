# ADR-034: SSR Hydration Race Condition with Controlled Form Inputs

**Status**: Accepted

**Decision type**: Architecture

**Date**: Sprint 11

## Context

During Sprint 11, we observed flaky Playwright E2E tests, especially on WebKit, affecting Login and Register forms.

Symptoms:

- Playwright filled input fields immediately after SSR render.
- React hydration subsequently overwrote the DOM values.
- The application submitted empty form values.
- Tests failed intermittently.

This was not purely a test issue — it represents a real hydration race condition between:

- Server-Side Rendering (SSR)
- Client-side React hydration
- Controlled React inputs (useState + value binding)

## Root Cause

Forms implemented as controlled components:

```tsx
const [email, setEmail] = useState("")
<input value={email} onChange={...} />
```

Hydration behavior:

1. Server sends HTML with empty input.
2. Browser renders it.
3. Playwright (or a fast user) fills input.
4. React hydrates and re-applies state value ("").
5. DOM value is overwritten.

WebKit exhibited this more frequently due to faster DOM/input timing.

## Architectural Insight

This is a known tradeoff in SSR + controlled inputs:
React state becomes the source of truth and overrides DOM state during hydration.

The issue is architectural, not tooling-related.

## Decision

For simple forms (login, register, checkout):

**We will migrate from controlled inputs to uncontrolled inputs**.

Instead of:

```ts
<input value={email} onChange={...} />
```

We will use:

```ts
<input name="email" defaultValue="" />
```

Form data will be collected via `FormData` on submit.

## Rationale

- Eliminates hydration overwrite risk.
- Removes race condition between SSR and hydration.
- Improves E2E test determinism.
- Preserves SSR benefits.
- Aligns with progressive enhancement principles.
- Avoids unnecessary React state usage.

Controlled inputs will be used only when real-time validation or dynamic behavior is required.

## Consequences

**Positive**

- Stable E2E tests across Chromium and WebKit.
- Cleaner form architecture.
- Better separation between SSR and client interactivity.

**Negative**

- Slight refactor effort required in form components.
- Must ensure validation is handled at submit time.

## Future Work

- Refactor LoginForm
- Refactor RegisterForm
- Refactor CheckoutForm
- Audit other forms for controlled input misuse

## References

- Next.js App Router hydration model
- React controlled vs uncontrolled inputs
- Playwright hydration race observations (Sprint 11)
