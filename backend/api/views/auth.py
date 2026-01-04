from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.tokens import RefreshToken

from api.serializers.auth import (
    RegisterRequestSerializer,
    LoginRequestSerializer,
    TokenResponseSerializer,
    UserResponseSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    authentication_classes = []  # allow unauthenticated
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Register user",
        request=RegisterRequestSerializer,
        responses={201: UserResponseSerializer},
    )
    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        email = serializer.validated_data.get("email")

        # Normalize empty email to None so DB-level uniqueness behaves predictably (esp. MySQL).
        if email == "":
            email = None

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                )
        except IntegrityError:
            # DB-level safety net for race conditions.
            # Map to DRF ValidationError -> global handler -> unified shape.
            errors = {}

            if User.objects.filter(username=username).exists():
                errors["username"] = ["This username is already taken."]

            if email is not None and User.objects.filter(email=email).exists():
                errors["email"] = ["This email is already taken."]

            if not errors:
                errors["non_field_errors"] = [
                    "Unable to register user due to a database constraint."]

            raise ValidationError(errors)

        return Response(UserResponseSerializer(user).data, status=201)


class LoginView(APIView):
    authentication_classes = []  # allow unauthenticated
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login user (JWT)",
        request=LoginRequestSerializer,
        responses={200: TokenResponseSerializer},
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            raise ValidationError(
                {"non_field_errors": ["Invalid username or password."]})

        refresh = RefreshToken.for_user(user)

        token_data = TokenResponseSerializer(
            {"access": str(refresh.access_token), "refresh": str(refresh)}
        )
        return Response(token_data.data, status=200)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Current user profile",
        responses={200: UserResponseSerializer},
    )
    def get(self, request):
        return Response(UserResponseSerializer(request.user).data)
