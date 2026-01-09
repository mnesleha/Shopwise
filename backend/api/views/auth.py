from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError, APIException
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework_simplejwt.tokens import RefreshToken

from carts.services.merge import merge_or_adopt_guest_cart
from carts.services.resolver import extract_cart_token
from api.serializers.auth import (
    RegisterRequestSerializer,
    LoginRequestSerializer,
    TokenResponseSerializer,
    UserResponseSerializer,
    RefreshRequestSerializer
)
from api.serializers.common import ErrorResponseSerializer

User = get_user_model()


class InvalidCredentials(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid email or password."
    default_code = "INVALID_CREDENTIALS"


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

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        first_name = serializer.validated_data.get("first_name", "")
        last_name = serializer.validated_data.get("last_name", "")

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    password=password,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
        except IntegrityError:
            # DB-level safety net for race conditions.
            # Map to DRF ValidationError -> global handler -> unified shape.
            errors = {}

            if User.objects.filter(email=email).exists():
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
        responses={
            200: TokenResponseSerializer,
            409: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Cart merge stock conflict",
                value={
                    "code": "CART_MERGE_STOCK_CONFLICT",
                    "message": "Insufficient stock to merge carts.",
                },
                response_only=True,
                status_codes=["409"],
            ),
        ],
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            raise InvalidCredentials()

        refresh = RefreshToken.for_user(user)

        cart_token = extract_cart_token(request)
        merge_or_adopt_guest_cart(user=user, raw_token=cart_token)

        token_data = TokenResponseSerializer(
            {"access": str(refresh.access_token), "refresh": str(refresh)}
        )
        response = Response(token_data.data, status=200)
        response.set_cookie(
            "cart_token",
            "",
            max_age=0,
            httponly=True,
            samesite="Lax",
            secure=getattr(settings, "CART_TOKEN_COOKIE_SECURE", False),
        )
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Current user profile",
        responses={200: UserResponseSerializer},
    )
    def get(self, request):
        return Response(UserResponseSerializer(request.user).data)


class RefreshView(APIView):
    authentication_classes = []  # refresh uses the refresh token in body
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Refresh access token",
        request=RefreshRequestSerializer,
        responses={200: TokenResponseSerializer},
    )
    def post(self, request):
        serializer = RefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_str = serializer.validated_data["refresh"]

        try:
            # This serializer applies:
            # - ROTATE_REFRESH_TOKENS
            # - BLACKLIST_AFTER_ROTATION (requires token_blacklist app + migrations)
            refresh_serializer = TokenRefreshSerializer(
                data={"refresh": refresh_str})
            refresh_serializer.is_valid(raise_exception=True)
            # dict with "access" and, when rotating, "refresh"
            data = refresh_serializer.validated_data
            return Response(TokenResponseSerializer(data).data, status=200)
        except Exception:
            # Map any refresh problems to our unified validation shape
            raise ValidationError(
                {"refresh": ["Invalid or expired refresh token."]})
