"""
Service layer for the password-reset flow.

Public API:
  - request_password_reset(email)           — anti-enumeration request endpoint
  - confirm_password_reset(token, new_password) — validate + apply reset
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import PASSWORD_RESET_EXPIRY_MINUTES, PasswordResetRequest
from accounts.services.session import logout_all_devices
from notifications.enqueue import enqueue_best_effort

logger = logging.getLogger(__name__)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def request_password_reset(email: str) -> None:
    """
    Initiate a password-reset flow for the given email address.

    Anti-enumeration contract: always returns silently (no exception) even
    if the email does not exist, so callers always respond 204.

    If the user exists:
    - Creates a PasswordResetRequest with a single-use hashed token.
    - Sends a best-effort email with a link pointing to the FRONTEND_BASE_URL.
    """
    try:
        user = User.objects.get(email__iexact=email.strip().lower())
    except User.DoesNotExist:
        # Silent no-op — do NOT reveal whether the address is registered.
        return

    raw_token = secrets.token_urlsafe(32)
    token_hash = _sha256(raw_token)
    now = timezone.now()

    req = PasswordResetRequest(
        user=user,
        token_hash=token_hash,
        expires_at=now + timedelta(minutes=PASSWORD_RESET_EXPIRY_MINUTES),
    )
    # Persist raw token in debug column when running in test mode so that
    # test helpers can retrieve it without intercepting outbound email.
    if getattr(settings, "STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS", False):
        req._token_debug = raw_token
    req.save()

    # Build the FE reset URL (not the API URL).
    frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
    reset_url = f"{frontend_base}/auth/reset-password?token={raw_token}"

    enqueue_best_effort(
        "notifications.jobs.send_password_reset_email",
        recipient_email=user.email,
        reset_url=reset_url,
    )


def confirm_password_reset(token: str, new_password: str) -> None:
    """
    Validate the reset token and apply the new password.

    Raises ValidationError (400) for:
    - Unknown / expired / already-used token.

    On success:
    - Sets the new password and saves.
    - Revokes all sessions (token_version++) so any outstanding JWT is rejected.
    - Marks the token as used (single-use enforcement).
    """
    now = timezone.now()
    token_hash = _sha256(token)

    try:
        req = PasswordResetRequest.objects.select_related("user").get(
            token_hash=token_hash
        )
    except PasswordResetRequest.DoesNotExist:
        raise ValidationError({"token": "Invalid or expired password-reset token."})

    if req.used_at is not None:
        raise ValidationError({"token": "This reset link has already been used."})

    if req.expires_at <= now:
        raise ValidationError({"token": "This reset link has expired."})

    user = req.user

    # Apply new password.
    user.set_password(new_password)
    user.save(update_fields=["password"])

    # Revoke all sessions — increments token_version so any outstanding refresh
    # token is rejected on its next use.
    logout_all_devices(user)

    # Mark token as used (single-use).
    req.used_at = now
    req.save(update_fields=["used_at"])
