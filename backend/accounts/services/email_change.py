"""
Service layer for the secure email-change flow (ADR-035).

Three public functions:
  - request_email_change(...)   — initiates the flow
  - confirm_email_change(token) — applies the new email + logout-all
  - cancel_email_change(token)  — cancels the pending request
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import EMAIL_CHANGE_EXPIRY_MINUTES, EmailChangeRequest
from auditlog.services import AuditService
from notifications.enqueue import enqueue_best_effort

logger = logging.getLogger(__name__)

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _generate_token_pair() -> tuple[str, str, str, str]:
    """Return (raw_confirm, hash_confirm, raw_cancel, hash_cancel)."""
    raw_confirm = secrets.token_urlsafe(32)
    raw_cancel = secrets.token_urlsafe(32)
    return raw_confirm, _sha256(raw_confirm), raw_cancel, _sha256(raw_cancel)


def _cancel_active_requests(user) -> None:
    """Cancel all currently active EmailChangeRequests for *user*."""
    now = timezone.now()
    EmailChangeRequest.objects.filter(
        user=user,
        confirmed_at__isnull=True,
        cancelled_at__isnull=True,
        expires_at__gt=now,
    ).update(cancelled_at=now)


def _blacklist_all_user_tokens(user) -> None:
    """
    Best-effort: blacklist every outstanding JWT refresh token for *user*.

    Uses the simplejwt token_blacklist app which must be installed (it is in
    this project). Failures are swallowed — the email change must not be
    rolled back because of a blacklist write error.
    """
    try:
        from rest_framework_simplejwt.token_blacklist.models import (  # noqa: PLC0415
            BlacklistedToken,
            OutstandingToken,
        )

        now = timezone.now()
        outstanding = OutstandingToken.objects.filter(
            user=user, expires_at__gt=now
        )
        for token_obj in outstanding:
            BlacklistedToken.objects.get_or_create(token=token_obj)
    except Exception:
        logger.warning(
            "Failed to blacklist JWT tokens for user_id=%s during email change confirm.",
            getattr(user, "pk", None),
            exc_info=True,
        )


def _emit_audit(*, action: str, user, metadata: dict | None = None) -> None:
    """Emit a best-effort audit event.  Never raises."""
    try:
        AuditService.emit(
            entity_type="user",
            entity_id=str(user.pk),
            action=action,
            actor_type="user",
            actor_user=user,
            metadata=metadata or {},
            fail_silently=True,
        )
    except Exception:
        logger.warning(
            "Audit event emission failed (best-effort). action=%s user_id=%s",
            action,
            getattr(user, "pk", None),
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@transaction.atomic
def request_email_change(
    user,
    *,
    new_email: str,
    current_password: str,
    request_ip: str | None = None,
    user_agent: str | None = None,
) -> EmailChangeRequest:
    """
    Initiate an email-change request for *user*.

    Steps:
    1. Normalise new_email (strip + lowercase).
    2. Verify current_password.
    3. Check new_email is not already taken (case-insensitive).
    4. Cancel any existing active request for the user.
    5. Create a new EmailChangeRequest (tokens are hashed; raw tokens are
       persisted to debug columns only when settings.DEBUG is True).
    6. Enqueue confirmation + cancellation emails (best-effort).
    7. Emit audit event (best-effort).
    """
    new_email = new_email.strip().lower()

    # Password check
    if not user.check_password(current_password):
        raise ValidationError({"current_password": ["Invalid password."]})

    # Uniqueness — case-insensitive across all users
    if User.objects.filter(email__iexact=new_email).exists():
        raise ValidationError({"new_email": ["This email address is already in use."]})

    # Cancel previous active request (idempotency invariant)
    _cancel_active_requests(user)

    # Generate tokens
    raw_confirm, hash_confirm, raw_cancel, hash_cancel = _generate_token_pair()

    expires_at = timezone.now() + timedelta(minutes=EMAIL_CHANGE_EXPIRY_MINUTES)

    ecr = EmailChangeRequest(
        user=user,
        old_email_snapshot=user.email,
        new_email=new_email,
        confirm_token_hash=hash_confirm,
        cancel_token_hash=hash_cancel,
        expires_at=expires_at,
        request_ip=request_ip,
        user_agent=user_agent,
    )

    # Persist raw tokens only when explicitly enabled for test environments.
    # Never persisted in production (STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS defaults to False).
    if getattr(settings, "STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS", False):
        ecr._confirm_token_debug = raw_confirm
        ecr._cancel_token_debug = raw_cancel

    ecr.save()

    # Build absolute URLs using PUBLIC_BASE_URL from settings.
    base = getattr(settings, "PUBLIC_BASE_URL", "").rstrip("/")
    confirm_url = f"{base}/account/confirm-email-change/?token={raw_confirm}"
    cancel_url = f"{base}/account/cancel-email-change/?token={raw_cancel}"

    # Best-effort: send confirmation email to new_email.
    try:
        enqueue_best_effort(
            "notifications.jobs.send_email_change_confirm",
            recipient_email=new_email,
            confirm_url=confirm_url,
        )
    except Exception:
        logger.warning(
            "Failed to enqueue email-change confirmation email (best-effort).",
            exc_info=True,
        )

    # Best-effort: send cancellation/notification email to old_email.
    try:
        enqueue_best_effort(
            "notifications.jobs.send_email_change_cancel_notification",
            recipient_email=user.email,  # old email
            cancel_url=cancel_url,
        )
    except Exception:
        logger.warning(
            "Failed to enqueue email-change cancellation email (best-effort).",
            exc_info=True,
        )

    # Best-effort audit
    _emit_audit(
        action="auth.email_change.requested",
        user=user,
        metadata={"new_email": new_email, "request_ip": request_ip},
    )

    return ecr


@transaction.atomic
def confirm_email_change(raw_token: str) -> EmailChangeRequest:
    """
    Confirm a pending email-change request.

    Steps:
    1. Look up the EmailChangeRequest by token hash.
    2. Validate it is active (not confirmed, not cancelled, not expired).
    3. Update User.email = new_email and mark email_verified = True.
    4. Mark the request as confirmed.
    5. Blacklist all outstanding JWT tokens for the user (logout-all).
    6. Emit audit event (best-effort).
    """
    if not isinstance(raw_token, str) or not raw_token.strip():
        raise ValidationError({"token": ["Confirm token is required."]})

    token_hash = _sha256(raw_token.strip())
    now = timezone.now()

    try:
        ecr = (
            EmailChangeRequest.objects.select_for_update()
            .select_related("user")
            .get(confirm_token_hash=token_hash)
        )
    except EmailChangeRequest.DoesNotExist:
        raise ValidationError({"token": ["Invalid or expired email-change token."]})

    if ecr.confirmed_at is not None:
        raise ValidationError({"token": ["This email-change request has already been confirmed."]})

    if ecr.cancelled_at is not None:
        raise ValidationError({"token": ["This email-change request has been cancelled."]})

    if ecr.expires_at <= now:
        raise ValidationError({"token": ["This email-change token has expired."]})

    user = ecr.user

    # Apply the email change.
    user.email = ecr.new_email
    user.email_verified = True
    user.save(update_fields=["email", "email_verified"])

    ecr.confirmed_at = now
    ecr.save(update_fields=["confirmed_at"])

    # Logout-all: blacklist all outstanding JWT tokens (best-effort).
    _blacklist_all_user_tokens(user)

    # Best-effort audit
    _emit_audit(
        action="auth.email_change.confirmed",
        user=user,
        metadata={"new_email": ecr.new_email, "old_email": ecr.old_email_snapshot},
    )

    return ecr


@transaction.atomic
def cancel_email_change(raw_token: str) -> EmailChangeRequest:
    """
    Cancel a pending email-change request.

    Steps:
    1. Look up the EmailChangeRequest by cancel token hash.
    2. Validate it is active (not already cancelled, not already confirmed, not expired).
    3. Mark the request as cancelled.
    4. Emit audit event (best-effort).
    """
    if not isinstance(raw_token, str) or not raw_token.strip():
        raise ValidationError({"token": ["Cancel token is required."]})

    token_hash = _sha256(raw_token.strip())
    now = timezone.now()

    try:
        ecr = (
            EmailChangeRequest.objects.select_for_update()
            .select_related("user")
            .get(cancel_token_hash=token_hash)
        )
    except EmailChangeRequest.DoesNotExist:
        raise ValidationError({"token": ["Invalid or expired email-change cancel token."]})

    if ecr.cancelled_at is not None:
        raise ValidationError({"token": ["This email-change request has already been cancelled."]})

    if ecr.confirmed_at is not None:
        raise ValidationError({"token": ["This email-change request has already been confirmed."]})

    if ecr.expires_at <= now:
        raise ValidationError({"token": ["This email-change cancel token has expired."]})

    ecr.cancelled_at = now
    ecr.save(update_fields=["cancelled_at"])

    # Best-effort audit
    _emit_audit(
        action="auth.email_change.cancelled",
        user=ecr.user,
        metadata={"new_email": ecr.new_email, "old_email": ecr.old_email_snapshot},
    )

    return ecr
