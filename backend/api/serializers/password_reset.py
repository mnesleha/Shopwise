"""
Serializers for the password-reset flow.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Validates a password-reset initiation request.

    Only validates that email is a valid email address format.
    We intentionally do NOT check whether the address exists here — that
    check happens in the service layer to preserve anti-enumeration semantics.
    """

    email = serializers.EmailField(
        help_text="Email address of the account to reset.",
    )


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Validates a password-reset confirmation request.

    Business rules:
    - new_password and new_password_confirm must be equal.
    - new_password passes Django's configured password validators.

    Token validity (existence, expiry, single-use) is checked in the service layer.
    """

    token = serializers.CharField(
        write_only=True,
        help_text="Single-use reset token received via email.",
    )
    new_password = serializers.CharField(
        write_only=True,
        help_text="The desired new password.",
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        help_text="Repeat the new password for confirmation.",
    )

    def validate(self, attrs: dict) -> dict:
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )

        # Run Django's built-in password validators.
        try:
            validate_password(attrs["new_password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": list(exc.messages)}
            )

        return attrs
