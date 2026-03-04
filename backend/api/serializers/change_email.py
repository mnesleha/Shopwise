"""
Serializers for the email-change flow (ADR-035).
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class ChangeEmailSerializer(serializers.Serializer):
    """
    Validates an email-change initiation request.

    Business rules applied here (fail-fast, detailed error messages):
    - new_email and new_email_confirm must match (after normalisation).
    - new_email must not already be in use by any account (case-insensitive).
    - current_password must match the authenticated user's password.

    The authenticated user is resolved from ``self.context["request"].user``.
    """

    new_email = serializers.EmailField(
        help_text="The requested new email address.",
    )
    new_email_confirm = serializers.EmailField(
        help_text="Repeat the new email address for confirmation.",
    )
    current_password = serializers.CharField(
        write_only=True,
        help_text="The user's current password (required for security).",
    )

    def validate(self, attrs: dict) -> dict:
        # Normalise both addresses identically to what the DB will store.
        new_email = attrs["new_email"].strip().lower()
        new_email_confirm = attrs["new_email_confirm"].strip().lower()

        if new_email != new_email_confirm:
            raise serializers.ValidationError(
                {"new_email_confirm": "Email addresses do not match."}
            )

        attrs["new_email"] = new_email

        # Uniqueness check — case-insensitive
        if User.objects.filter(email__iexact=new_email).exists():
            raise serializers.ValidationError(
                {"new_email": "This email address is already in use."}
            )

        # Password verification
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Invalid password."}
            )

        return attrs
