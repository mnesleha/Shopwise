# ADR-029: Audit Log Baseline (Orders)

**Status**: Accepted

**Date**: Sprint 11

**Decision type**: Architecture

**Related**: Auth module, Orders API, Frontend SSR integration

## Context

The project originally used JWT tokens returned in JSON responses and stored client-side.
As frontend complexity increased (Next.js App Router + SSR order pages), several architectural constraints emerged:

1. Server-side rendering (SSR) requires authentication context.
2. Storing JWT in localStorage does not work for SSR.
3. Passing JWT via Authorization header from client only covers CSR scenarios.
4. Security best practices discourage storing long-lived tokens in localStorage due to XSS risks.
5. The application requires:
   - Authenticated order detail via SSR (/orders/{id})
   - Automatic token refresh
   - Logout with proper token invalidation
   - Guest checkout flow running independently of JWT

A unified, secure, SSR-compatible authentication strategy was required.

## Decision

JWT authentication is implemented using httpOnly cookies for both access and refresh tokens.

### Cookie-Based Token Storage

On successful login:

- `access_token` → stored in httpOnly cookie
- `refresh_token` → stored in httpOnly cookie
- Cookies are configured with:
  - HttpOnly = true
  - Path = /
  - Secure = not DEBUG
  - SameSite = Lax (suitable for same-site proxy setup)

No tokens are stored in `localStorage`.

### Backend Authentication Strategy

A custom authentication class `CookieJWTAuthentication` extends `JWTAuthentication`:

- Attempts standard `Authorization` header first.
- Falls back to `access_token` cookie.
- Allows DRF `IsAuthenticated` permissions to work transparently.

This ensures:

- API compatibility with standard JWT flows.
- SSR compatibility without custom headers.
- No frontend token injection.

### SSR Forwarding Strategy (Next.js App Router)

Next.js Server Components execute server-to-server fetch calls to the Django backend.

Since cookies are not automatically forwarded in SSR:

- `cookies()` from `next/headers` is used.
- Only relevant cookies (`access_token`, `refresh_token`, etc.) are manually forwarded.
- The `Cookie` header is constructed explicitly.

This ensures:

- SSR pages (e.g., `/orders/{id}`) authenticate correctly.
- No reliance on client-side state.
- Full compatibility with App Router dynamic APIs (Next 16 async `cookies()`).

### Automatic Token Refresh

Frontend axios interceptor:

- On `401` (excluding auth endpoints), calls `/auth/refresh/`.
- Refresh endpoint reads `refresh_token` from cookie.
- Issues new `access_token` (and rotated `refresh_token` if enabled).
- Retries original request.
- On refresh failure → redirect to `/login`.

Refresh endpoint no longer depends on request body.

### Logout Strategy

`POST /api/v1/auth/logout/`:

- Deletes `access_token` and `refresh_token` cookies.
- Frontend resets auth context.
- Redirects to public route.

### Session Probe Endpoint

`GET /api/v1/auth/me/`:

- `AllowAny`
- Returns:
  - `{ is_authenticated: true, ...userData }`
  - `{ is_authenticated: false }`

Used by `AuthProvider` to:

- Initialize session state
- Toggle Login / Logout UI
- Drive authenticated checkout routing

## Consequences

**Positive**

- SSR-compatible authentication.
- Eliminates XSS risk of token exposure via localStorage.
- Clean separation of guest and authenticated flows.
- Transparent DRF permission handling.
- Production-ready pattern compatible with reverse proxy or separate host deployment.
- Clear architecture suitable for SaaS / white-label deployment.

**Trade-offs**

- Slightly increased implementation complexity.
- Requires explicit cookie forwarding in SSR.
- Requires careful interceptor configuration to avoid refresh loops.
- Requires cookie-based refresh endpoint implementation.

## Alternatives Considered

### JWT in localStorage

Rejected:

- Not SSR-compatible.
- XSS exposure risk.

### Session-based auth (Django session)

Rejected:

- Less portable for stateless API usage.
- JWT better aligned with existing architecture.

### Custom BFF token translation layer

Not implemented:

- Would add complexity without additional benefit at current scale.

## Security Considerations

- httpOnly prevents JavaScript access to tokens.
- Secure flag enforced in production.
- SameSite prevents CSRF in same-site proxy configuration.
- CSRF protection remains enabled for state-changing endpoints where applicable.
- No token exposure in frontend memory.

## Architectural Impact

This decision establishes:

- JWT as transport format.
- Cookies as storage medium.
- SSR forwarding as infrastructure requirement.
- Unified authentication strategy for:
  - Authenticated checkout
  - Authenticated order history
  - Order detail SSR
  - Future account pages

This ADR formalizes authentication as infrastructure-level architecture, not feature-level logic.
