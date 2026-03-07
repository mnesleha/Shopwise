# ADR-036: API Throttling Strategy

**Status**: Accepted

**Decision type**: Architecture

**Date**: Sprint 12

## Context

Shopwise exposes public and authenticated API endpoints related to authentication, account security, and email-based recovery flows. Several of these endpoints are attractive targets for abuse, including brute-force attacks, credential stuffing, spam, token guessing, and infrastructure-level request flooding.

During Sprint 12, authentication-related backend findings revealed that security-sensitive endpoints needed explicit request throttling to protect both user accounts and infrastructure. The project uses cookie-based JWT authentication and includes flows such as login, refresh, change email, change password, password reset, and email verification resend.

The throttling strategy must:

- protect critical endpoints from abuse,
- remain understandable and maintainable,
- support local development and automated tests without excessive friction,
- allow future tuning through configuration rather than code changes.

## Decision

Shopwise adopts explicit application-level throttling for selected endpoints using per-key rate limits backed by a shared rate-limiting utility.

### Throttle dimensions

Depending on the endpoint, throttling is applied by one or more of the following keys:

- **Per IP address** — protects infrastructure and mitigates broad abuse/spam.
- **Per email address** — protects identity-oriented flows such as login and email verification resend.
- **Per authenticated user** — protects authenticated account operations such as change password and logout-all.

### Current coverage

The following endpoint groups are throttled:

#### Authentication

- **Register**
  - per IP
- **Login**
  - per IP
  - per email
- **Refresh**
  - per IP
- **Logout**
  - per IP

#### Account security

- **Change email**
  - per IP
  - per authenticated user
- **Confirm email change**
  - per IP
- **Cancel email change**
  - per IP
- **Logout from all devices**
  - per authenticated user
- **Change password**
  - per IP
  - per authenticated user

#### Email / recovery

- **Resend email verification**
  - per IP
  - per email
- **Password reset request**
  - per IP
- **Password reset confirm**
  - per IP

### Behavioral rules

- Where multiple throttle dimensions apply to a single endpoint, **all counters are incremented** for every request. The request is rejected with HTTP 429 if any configured limit is exceeded.
- Login is intentionally throttled by both IP and email to mitigate credential stuffing without relying only on one dimension.
- Refresh is throttled by IP to reduce abuse and protect infrastructure.
- Token-based GET endpoints (such as confirm/cancel email change) are also throttled by IP to reduce abuse and token-guessing attempts.

### Configuration

Throttle limits are configured through settings constants rather than hard-coded values. This allows:

- permissive values in local development,
- test-safe values in test settings,
- stricter values in production.

A dedicated test bypass flag is used for automated tests where necessary so that functional tests are not destabilized by throttling behavior.

## Consequences

**Positive**

- Protects the most abuse-prone endpoints without introducing infrastructure-level complexity.
- Keeps throttling rules explicit and easy to reason about.
- Allows future tuning without refactoring endpoint logic.
- Supports layered protection: infrastructure safety, identity safety, and authenticated-account safety.

**Trade-offs**

- Adds some configuration overhead and repeated rate-limit checks in views.
- Requires discipline to keep coverage aligned as new auth/account endpoints are introduced.
- Test bypass behavior must remain explicit and carefully named to avoid accidental misuse.

## Alternatives Considered

1. No application-level throttling

   Rejected because authentication and recovery endpoints are high-risk abuse targets.

2. Infrastructure-only throttling (reverse proxy / CDN / WAF)

   Rejected as insufficient on its own because application-level keys such as email and authenticated user are not always visible at the edge.

3. Global throttling only by IP

   Rejected because IP-only throttling is too coarse for identity-sensitive flows such as login and resend verification.

## Notes

This ADR defines the throttling methodology and endpoint coverage pattern. Specific throttle values are operational concerns and may evolve over time without changing this architectural decision.

Future candidates for throttling must be evaluated whenever new auth, guest-email, or token-confirmation flows are introduced.
