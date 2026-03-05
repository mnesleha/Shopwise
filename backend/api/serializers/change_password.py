"""
Serializer for the change-password endpoint.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class ChangePasswordSerializer(serializers.Serializer):
    """
    Validates a password-change request.

    Business rules:
    - current_password must match the user's existing password.
    - new_password and new_password_confirm must be equal.
    - new_password passes Django's configured password validators.

    The authenticated user is resolved from ``self.context["request"].user``.
    """

    current_password = serializers.CharField(
        write_only=True,
        help_text="The user's current password.",
    )
    new_password = serializers.CharField(
        write_only=True,
        help_text="The desired new password.",
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        help_text="Repeat the new password for confirmation.",
    )

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Invalid password.")
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )

        # Run Django's built-in password validators (length, common passwords, etc.)
        user = self.context["request"].user
        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": list(exc.messages)}
            )

        return attrs
