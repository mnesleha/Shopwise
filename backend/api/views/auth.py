from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError, APIException
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework_simplejwt.tokens import RefreshToken

from config.settings.base import auth_cookie_kwargs
from carts.services.merge import merge_or_adopt_guest_cart
from carts.services.resolver import extract_cart_token
from accounts.services.email_verification import (
    issue_email_verification_token,
    verify_email_verification_token,
)
from orders.services.claim import claim_guest_orders_for_user
from django_q.tasks import async_task
from api.services.cookies import cart_token_cookie_kwargs
from api.serializers.auth import (
    RegisterRequestSerializer,
    LoginRequestSerializer,
    TokenResponseSerializer,
    UserResponseSerializer,
    RefreshRequestSerializer,
    VerifyEmailRequestSerializer,
    VerifyEmailResponseSerializer,
    RequestEmailVerificationRequestSerializer,
    RequestEmailVerificationResponseSerializer,
)
from api.serializers.common import ErrorResponseSerializer
from api.services.rate_limit import rate_limit_hit
from notifications.enqueue import enqueue_best_effort
from notifications.error_handler import NotificationErrorHandler
from notifications.exceptions import NotificationSendError

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

        claimed_orders = 0
        if getattr(user, "email_verified", False):
            claimed_orders = claim_guest_orders_for_user(user)

        token_data = TokenResponseSerializer(
            {"access": str(refresh.access_token), "refresh": str(refresh)}
        )

        access_str = str(refresh.access_token)
        refresh_str = str(refresh)

        # Include claim report so frontend can show a toast and E2E tests can assert behavior.
        # NOTE: TokenResponseSerializer/OpenAPI schema should be updated accordingly in a follow-up refactor.
        response_payload = dict(token_data.data)
        response_payload["claimed_orders"] = claimed_orders

        response = Response(response_payload, status=200)
        
        response.set_cookie(
            "cart_token",
            "",
            max_age=0,
            **cart_token_cookie_kwargs()
        )

        response.set_cookie(settings.AUTH_COOKIE_ACCESS, access_str, **auth_cookie_kwargs())
        response.set_cookie(settings.AUTH_COOKIE_REFRESH, refresh_str, **auth_cookie_kwargs())

        return response


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        resp = Response({"ok": True}, status=200)

        access_cookie_name = getattr(settings, "AUTH_COOKIE_ACCESS", "access_token")
        refresh_cookie_name = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")

        resp.delete_cookie(access_cookie_name, path=getattr(settings, "AUTH_COOKIE_PATH", "/"))
        resp.delete_cookie(refresh_cookie_name, path=getattr(settings, "AUTH_COOKIE_PATH", "/"))

        return resp


class MeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Current user profile",
        responses={200: UserResponseSerializer},
    )
    def get(self, request):
        if request.user.is_authenticated:
            data = UserResponseSerializer(request.user).data
            data["is_authenticated"] = True
            return Response(data, status=200)

        return Response({"is_authenticated": False, "email_verified": False}, status=200)


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Refresh access token",
        request=RefreshRequestSerializer,
        responses={200: TokenResponseSerializer},
    )
    
    def post(self, request):
        # Prefer cookie (httpOnly) for refresh
        refresh_cookie_name = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")
        refresh_str = request.COOKIES.get(refresh_cookie_name) or request.data.get("refresh")

        # Fallback to body for backwards compatibility (optional)
        if not refresh_str:
          refresh_str = request.data.get("refresh")

        if not refresh_str:
            raise ValidationError({"refresh": ["Missing refresh token."]})

        try:
            refresh_serializer = TokenRefreshSerializer(data={"refresh": refresh_str})
            refresh_serializer.is_valid(raise_exception=True)
            data = refresh_serializer.validated_data  # has "access" and sometimes "refresh" if rotating

            resp = Response(TokenResponseSerializer(data).data, status=200)

            # Always set new access cookie
            access_cookie_name = getattr(settings, "AUTH_COOKIE_ACCESS", "access_token")
            resp.set_cookie(access_cookie_name, data["access"], **auth_cookie_kwargs())

            # If rotation is enabled, set new refresh cookie too
            if "refresh" in data:
                resp.set_cookie(refresh_cookie_name, data["refresh"], **auth_cookie_kwargs())

            return resp
        except Exception:
            raise ValidationError({"refresh": ["Invalid or expired refresh token."]})


class VerifyEmailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Verify email via token",
        request=VerifyEmailRequestSerializer,
        responses={200: VerifyEmailResponseSerializer},
    )
    def post(self, request):
        """
        Performs the actual email verification.
        Used by API clients and by the confirmation form.
        """
        serializer = VerifyEmailRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        _, claimed = verify_email_verification_token(
            serializer.validated_data["token"],
            request=request,
        )

        return Response(
            {"email_verified": True, "claimed_orders": claimed},
            status=200,
        )

    def get(self, request):
        """
        Used by clickable email links.
        Renders confirmation page only.
        """
        token = request.query_params.get("token")
        if not token:
            return HttpResponseBadRequest("Missing verification token")

        # We do NOT verify here — only render confirmation page
        return render(
            request,
            "auth/verify_email_confirm.html",
            {"token": token},
        )


class RequestEmailVerificationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Request email verification",
        request=RequestEmailVerificationRequestSerializer,
        responses={202: RequestEmailVerificationResponseSerializer},
    )
    def post(self, request):
        serializer = RequestEmailVerificationRequestSerializer(
            data=request.data)
        serializer.is_valid(raise_exception=True)

        # IMPORTANT:
        # - Always respond 202 to avoid user enumeration.
        # - Best-effort side effect: if anything goes wrong, we do not block the request.
        email = serializer.validated_data["email"].strip().lower()

        # Lightweight throttling to prevent abuse (best-effort).
        # Defaults can be overridden in settings.
        per_email_limit = int(
            getattr(settings, "EMAIL_VERIFICATION_RL_PER_EMAIL", 3))
        per_ip_limit = int(
            getattr(settings, "EMAIL_VERIFICATION_RL_PER_IP", 20))
        window_s = int(
            getattr(settings, "EMAIL_VERIFICATION_RL_WINDOW_S", 300))

        ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[
            0].strip() or request.META.get("REMOTE_ADDR") or "unknown"
        limited = rate_limit_hit(
            key=f"rl:email_verification:email:{email}",
            limit=per_email_limit,
            window_s=window_s,
        ) or rate_limit_hit(
            key=f"rl:email_verification:ip:{ip}",
            limit=per_ip_limit,
            window_s=window_s,
        )

        if limited:
            return Response({"queued": True}, status=202)

        user = User.objects.filter(email=email).first()

        if user and not user.email_verified:
            try:
                raw_token = issue_email_verification_token(user)
                verification_url = (
                    f"{settings.PUBLIC_BASE_URL}"
                    f"/verify-email/?token={raw_token}"
                )

                def _enqueue() -> None:
                    enqueue_best_effort(
                        "notifications.jobs.send_email_verification",
                        recipient_email=user.email,
                        verification_url=verification_url,
                    )

                transaction.on_commit(_enqueue)
            except Exception:
                NotificationErrorHandler.handle(
                    NotificationSendError(
                        code="EMAIL_VERIFICATION_INTENT_FAILED",
                        message="Failed to prepare email verification notification intent.",
                        context={
                            "email": email,
                            "user_id": getattr(user, "id", None),
                        },
                    )
                )
                return Response({"queued": True}, status=202)

        return Response({"queued": True}, status=202)
