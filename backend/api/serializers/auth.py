from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueValidator


class RegisterRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        normalized = value.strip().lower()
        User = get_user_model()
        validator = UniqueValidator(
            queryset=User.objects.all(),
            message="This email is already taken.",
        )
        validator(normalized, self.fields["email"])
        return normalized


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.strip().lower()


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        return "ADMIN" if obj.is_staff or obj.is_superuser else "CUSTOMER"
