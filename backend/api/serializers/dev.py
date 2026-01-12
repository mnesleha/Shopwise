from rest_framework import serializers


class DevEmailVerificationTokenRequestSerializer(serializers.Serializer):
    email = serializers.CharField()

    def validate_email(self, value):
        if not isinstance(value, str) or not value.strip():
            raise serializers.ValidationError("This field is required.")
        return value.strip()


class DevEmailVerificationTokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
