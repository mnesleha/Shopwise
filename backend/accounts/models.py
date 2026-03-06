import hashlib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django_countries.fields import CountryField


class UserManager(BaseUserManager):
    """
    Custom user manager for an email-first identity model.
    - Email is the primary identifier (USERNAME_FIELD = email).
    - Username is retained for Django compatibility only and is derived
      deterministically from email.
    """

    use_in_migrations = True

    @staticmethod
    def _username_from_email(email: str) -> str:
        """
        Django's AbstractUser username has max_length=150. For very long emails,
        use a stable hash-based username to avoid DB errors.
        """
        if len(email) <= 150:
            return email
        digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]
        return f"u_{digest}"

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address must be provided.")

        normalized_email = self.normalize_email(email).strip().lower()
        # Username is not an API/public identity field. We ignore any provided
        # username and derive it from email for compatibility.
        derived_username = self._username_from_email(normalized_email)

        user = self.model(
            email=normalized_email, username=derived_username, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email=email, password=password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email=email, password=password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True)
    email_verified = models.BooleanField(default=False, db_index=True)
    # Incremented on logout-all / email change to invalidate all outstanding
    # refresh tokens that carry a stale tv (token_version) claim.
    token_version = models.PositiveIntegerField(default=1)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        # Ensure username is always set, regardless of the creation path
        # (admin form, management command, tests, etc.).
        if not self.username and self.email:
            self.username = UserManager._username_from_email(
                self.email.strip().lower()
            )
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        parts = [p for p in (self.first_name, self.last_name) if p]
        full_name = " ".join(parts).strip()
        return full_name or self.email


class CustomerProfile(models.Model):
    """
    Extends the built-in User with e-commerce profile data (1:1).
    Created automatically via a post_save signal on User.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    default_shipping_address = models.ForeignKey(
        "Address",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    default_billing_address = models.ForeignKey(
        "Address",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    def clean(self) -> None:
        """
        Validate that default addresses belong to this profile.
        Called by full_clean().
        """
        from django.core.exceptions import ValidationError

        errors = {}
        for field_name in ("default_shipping_address", "default_billing_address"):
            address = getattr(self, field_name)
            if address is not None and address.profile_id != self.pk:
                errors[field_name] = (
                    "Address does not belong to this profile."
                )
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"CustomerProfile(user_id={self.user_id})"


class Address(models.Model):
    """
    A physical address belonging to a CustomerProfile.
    One profile can have many addresses.
    """

    profile = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    street_line_1 = models.CharField(max_length=255)
    street_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=32)
    # ISO 3166-1 alpha-2 country code; validated via django-countries
    country = CountryField()
    company = models.CharField(max_length=255, blank=True)
    vat_id = models.CharField(max_length=64, blank=True)

    def __str__(self) -> str:
        return f"Address(profile_id={self.profile_id}, city={self.city})"


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    used_ip = models.GenericIPAddressField(null=True, blank=True)
    used_user_agent = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return f"EmailVerificationToken(user_id={self.user_id})"


# ---------------------------------------------------------------------------
# Email change flow
# ---------------------------------------------------------------------------

EMAIL_CHANGE_EXPIRY_MINUTES = 60  # Single-use tokens expire after 60 minutes.


class EmailChangeRequest(models.Model):
    """
    Represents a pending email-change request.

    Invariant: at most one active request per user.
    Active = confirmed_at is None AND cancelled_at is None AND expires_at > now.

    Token handling:
    - Two random raw tokens (confirm + cancel) are generated by the service layer.
    - Only their SHA-256 hashes are stored in the production columns.
    - When settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS is True the *raw* tokens
      are also persisted in the ``*_debug`` columns so that integration tests can
      retrieve them without intercepting outbound email.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_change_requests",
    )
    old_email_snapshot = models.EmailField()
    new_email = models.EmailField()
    confirm_token_hash = models.CharField(max_length=64, db_index=True)
    cancel_token_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Optional audit / security fields
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Test-only: raw tokens stored only when settings.DEBUG is True.
    # These columns are always NULL in production / non-debug environments.
    # ------------------------------------------------------------------
    _confirm_token_debug = models.CharField(
        max_length=128, null=True, blank=True, db_column="confirm_token_debug"
    )
    _cancel_token_debug = models.CharField(
        max_length=128, null=True, blank=True, db_column="cancel_token_debug"
    )

    def __str__(self) -> str:
        return (
            f"EmailChangeRequest(user_id={self.user_id}, new_email={self.new_email})"
        )

    # ------------------------------------------------------------------
    # Test helpers (only usable when DEBUG=True)
    # ------------------------------------------------------------------

    def get_confirm_token_for_tests(self) -> str:
        """
        Return the raw confirm token.

        Only works when settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS is True
        (set that flag in test settings; the service layer then persists the
        raw token to the _confirm_token_debug column).
        Raises RuntimeError in production / non-test mode.
        """
        from django.conf import settings as _settings  # local import to avoid circularity

        if not getattr(_settings, "STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS", False):
            raise RuntimeError(
                "get_confirm_token_for_tests() requires settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS = True."
            )
        # Reload from DB in case the instance pre-dates the service call.
        if self._confirm_token_debug is None:
            self.refresh_from_db(fields=["_confirm_token_debug"])
        return self._confirm_token_debug

    def get_cancel_token_for_tests(self) -> str:
        """
        Return the raw cancel token.

        Only works when settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS is True
        (set that flag in test settings; the service layer then persists the
        raw token to the _cancel_token_debug column).
        Raises RuntimeError in production / non-test mode.
        """
        from django.conf import settings as _settings

        if not getattr(_settings, "STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS", False):
            raise RuntimeError(
                "get_cancel_token_for_tests() requires settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS = True."
            )
        if self._cancel_token_debug is None:
            self.refresh_from_db(fields=["_cancel_token_debug"])
        return self._cancel_token_debug


# ---------------------------------------------------------------------------
# Password reset flow
# ---------------------------------------------------------------------------

PASSWORD_RESET_EXPIRY_MINUTES = 60  # Single-use tokens expire after 60 minutes.


class PasswordResetRequest(models.Model):
    """
    Represents a single-use password-reset request.

    Token handling:
    - A random raw token is generated by the service layer.
    - Only its SHA-256 hash is stored in the production column (token_hash).
    - When settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS is True the *raw* token
      is also persisted in the _token_debug column so that integration tests can
      retrieve it without intercepting outbound email.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_requests",
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    # Test-only: raw token stored only when STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS is True.
    # Always NULL in production / non-debug environments.
    _token_debug = models.CharField(
        max_length=128, null=True, blank=True, db_column="token_debug"
    )

    def __str__(self) -> str:
        return f"PasswordResetRequest(user_id={self.user_id}, used={self.used_at is not None})"

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    @classmethod
    def create_for_user_for_tests(cls, *, user) -> "PasswordResetRequest":
        """
        Create a PasswordResetRequest directly in the DB for testing purposes.

        Bypasses the service layer (no email sent).  Stores the raw token in
        the _token_debug column so that get_token_for_tests() can retrieve it.
        """
        import secrets as _secrets

        raw = _secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        now = timezone.now()
        req = cls.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=now + timedelta(minutes=PASSWORD_RESET_EXPIRY_MINUTES),
            _token_debug=raw,
        )
        return req

    def get_token_for_tests(self) -> str:
        """
        Return the raw reset token stored in the debug column.

        Raises RuntimeError unless settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS
        is True (set in test settings).
        """
        from django.conf import settings as _settings

        if not getattr(_settings, "STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS", False):
            raise RuntimeError(
                "get_token_for_tests() requires settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS = True."
            )
        if self._token_debug is None:
            self.refresh_from_db(fields=["_token_debug"])
        return self._token_debug
