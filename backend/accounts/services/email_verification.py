import hashlib
import secrets
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import EmailVerificationToken
from orders.services.claim import claim_guest_orders_for_user


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def issue_email_verification_token(user, *, ttl_minutes: int = 60 * 24) -> str:
    attempts = 5
    expires_at = timezone.now() + timedelta(minutes=ttl_minutes)

    for _ in range(attempts):
        raw_token = secrets.token_urlsafe(32)
        token_hash = sha256_hex(raw_token)
        try:
            EmailVerificationToken.objects.create(
                user=user,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        except IntegrityError:
            continue
        return raw_token

    raise ValidationError(
        {"token": ["Unable to issue email verification token."]})


def verify_email_verification_token(raw_token: str, *, request=None):
    if not isinstance(raw_token, str) or not raw_token.strip():
        raise ValidationError(
            {"token": ["Email verification token is required."]})

    token_hash = sha256_hex(raw_token.strip())
    now = timezone.now()

    with transaction.atomic():
        try:
            token = (
                EmailVerificationToken.objects.select_for_update()
                .select_related("user")
                .get(token_hash=token_hash)
            )
        except EmailVerificationToken.DoesNotExist:
            raise ValidationError(
                {"token": ["Invalid or expired email verification token."]}
            )

        if token.used_at is not None or token.expires_at <= now:
            raise ValidationError(
                {"token": ["Invalid or expired email verification token."]}
            )

        token.used_at = now
        if request is not None:
            token.used_ip = request.META.get("REMOTE_ADDR")
            ua = request.META.get("HTTP_USER_AGENT") or ""
            token.used_user_agent = ua[:512] or None
        token.save(update_fields=["used_at", "used_ip", "used_user_agent"])

        user = token.user
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])

        claimed_count = claim_guest_orders_for_user(user)

    return user, claimed_count
