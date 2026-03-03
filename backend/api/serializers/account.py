from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class AccountSerializer(serializers.ModelSerializer):
    """
    Serializer for the authenticated user's own account identity.

    Read-only fields: email, email_verified.
    Writable fields: first_name, last_name.

    Explicitly rejects any attempt to supply `email` in the request body.
    """

    email = serializers.EmailField(read_only=True)
    email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "email_verified"]

    def validate(self, attrs):
        # Reject email changes at the serializer level regardless of partial mode.
        # E-mail address changes require a separate reverification flow.
        if "email" in self.initial_data:
            raise serializers.ValidationError(
                {"email": "Email cannot be changed via this endpoint."}
            )
        return super().validate(attrs)
