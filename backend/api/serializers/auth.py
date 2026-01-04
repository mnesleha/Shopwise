from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.validators import UniqueValidator


class RegisterRequestSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="This username is already taken.",
            )
        ],
    )
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(
        required=False,
        allow_null=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.exclude(
                    email__isnull=True).exclude(email=""),
                message="This email is already taken.",
            )
        ],
    )


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class UserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        return "ADMIN" if obj.is_staff or obj.is_superuser else "CUSTOMER"
