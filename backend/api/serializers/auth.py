from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueValidator


class RegisterRequestSerializer(serializers.Serializer):
    User = get_user_model()

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
        allow_blank=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.exclude(
                    email__isnull=True).exclude(email=""),
                message="This email is already taken.",
            )
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["email"].validators.append(
            UniqueValidator(queryset=User.objects.all())
        )

    def validate_email(self, value):
        # Normalize empty string to None to ensure consistent DB storage
        # and predictable uniqueness behavior (especially on MySQL).
        if value == "":
            return None
        return value

    def validate_username(self, value):
        return value.lower()


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        return "ADMIN" if obj.is_staff or obj.is_superuser else "CUSTOMER"
