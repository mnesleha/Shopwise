import hashlib
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


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

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def display_name(self) -> str:
        parts = [p for p in (self.first_name, self.last_name) if p]
        full_name = " ".join(parts).strip()
        return full_name or self.email


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
