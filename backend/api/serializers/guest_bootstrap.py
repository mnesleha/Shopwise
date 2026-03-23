"""
Serializers for the guest-order bootstrap (guest → account) endpoint.
"""
from rest_framework import serializers


class GuestBootstrapRequestSerializer(serializers.Serializer):
    """
    Input for POST /api/v1/guest/orders/{id}/bootstrap/.

    Only the password is required — all other identity data is taken from the
    already-verified order snapshot.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=1,
        help_text="Password for the new account.",
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=1,
        help_text="Must match password.",
    )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs


class GuestBootstrapResponseSerializer(serializers.Serializer):
    """
    Successful bootstrap response — mirrors the shape of UserResponseSerializer
    so the frontend can treat it uniformly.
    """

    is_authenticated = serializers.BooleanField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    role = serializers.SerializerMethodField()
    email_verified = serializers.BooleanField(read_only=True)

    def get_role(self, obj) -> str:
        return "ADMIN" if obj.is_staff or obj.is_superuser else "CUSTOMER"
