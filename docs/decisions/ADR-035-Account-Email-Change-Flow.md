# ADR-035: Account Email Change Flow (Confirm + Block + Logout All)

**Status**: Accepted

**Decision type**: Architecture

**Date**: Sprint 12

## Context

Shopwise uses cookie-based JWT authentication (access + refresh) and exposes /auth/me as a read-only session probe used frequently by the frontend (SSR and client). Users need to be able to change their login email address securely.

Key requirements:

- Prevent account takeover from an unlocked device by requiring current password.
- Avoid locking users out due to typos by requiring email confirmation input.
- Do not change the primary login email in the database until the new email is verified.
- Send a verification link to the new email and a security notification to the old email with a one-click “block/cancel” action.
- After confirmation, terminate all active sessions (logout-all) and redirect the user to login.
- Orders must remain linked to user_id (email used only for guest order claiming lookup).

## Decision

We implement a dedicated, versioned email change flow under /api/v1/account/ using a separate database model for pending requests.

### Data model

Introduce `EmailChangeRequest` to store pending email changes:

- `user` (FK)
- `old_email_snapshot`
- `new_email`
- `confirm_token_hash` + expiry
- `cancel_token_hash` + expiry (or a distinct token)
- timestamps: `created_at`, `expires_at`, `confirmed_at`, `cancelled_at`
- optional: `request_ip`, `user_agent` for audit and security review

### API endpoints (v1)

- `POST /api/v1/account/change-email/`
  - input: `new_email`, `new_email_confirm`, `current_password`
  - creates a pending `EmailChangeRequest`
  - sends:
    - confirmation email to `new_email` with confirm link
    - notification email to `old_email_snapshot` with cancel link
  - does not change `User.email` yet
- `GET /api/v1/account/confirm-email-change/?token=...`
  - validates token and request state
  - sets `User.email = new_email` (login identifier remains unique)
  - treats confirmation click as email verification (no separate verify step)
  - invalidates all active sessions (logout-all)
- `POST /api/v1/account/cancel-email-change/`
- validates cancel token
- marks the request as cancelled, preventing confirmation

### Authentication/session probe

`/auth/me` remains GET-only and should not implement email change or other account mutations. It may include read-only `email`, `first_name`, `last_name`, and `email_verified` for UI personalization and guards.

### Security behavior

- Current password is required to initiate email change.
- Email must be entered twice to reduce typo risk.
- Confirmation token is single-use and time-limited.
- “One-click block” via cancel token prevents completion if the request is not legitimate.
- After a successful change, all sessions are terminated and the user must log in again with the new email.

### Rate limiting

- `POST /api/v1/account/change-email/` is throttled per user and per IP to reduce abuse (spam/brute force).

### Normalization & uniqueness

- Emails are normalized (trim + lowercase) before comparison.
- New email must be unique across all users (case-insensitive).

### Single active request invariant

- At most one active `EmailChangeRequest` exists per user.
- Creating a new request automatically cancels any previous active request for the same user.

### One-click cancel link

- Cancellation is performed via a clickable GET endpoint:
  - `GET /api/v1/account/cancel-email-change/?token=...`
- This is an explicit UX-over-purity trade-off accepted for incident response speed.

### Audit log emission

- Emit best-effort audit events via the auditlog service-layer:
  - `auth.email_change.requested`
  - `auth.email_change.confirmed`
  - `auth.email_change.cancelled`
- Audit failures must not block the primary flow.

## Consequences

**Positive**:

- Strong protection against account takeover and silent email hijack.
- Clear audit trail of email change attempts.
- Keeps `/auth/me` stable and lightweight.
- Aligns with best practices: verify new email, notify old email, block action, logout-all.
- Improved security posture due to throttling + notification + one-click cancel.
- Clear audit trail aligned with [ADR-029](./ADR-029-Audit-Log-Baseline-Orders.md) principles (service-layer, best-effort).

**Trade-offs**:

- More components than a simple `PATCH /account` (additional model, two emails, token lifecycle).
- Requires careful token handling (hashing, expiry, single-use).
- Slightly more complexity (request lifecycle + token handling), accepted.

## Alternatives Considered

- Immediate email update + separate verification
  - Rejected: can lock user out and complicate rollback; also increases risk if email is changed without confirmation.
- Reusing `/auth/me` for mutations
  - Rejected: would mix session probing with account management and risk turning it into an orchestration endpoint.
- Polling status endpoint
  - Rejected: low value for this flow; adds complexity without improving security or UX meaningfully.

## Notes

Orders remain associated by `user_id` and store snapshot fields for historical integrity. Email is only used as a lookup key for guest order claiming and should not be the primary relationship key.
