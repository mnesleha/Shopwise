from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed, ValidationError, APIException
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework_simplejwt.tokens import RefreshToken

from config.settings.base import auth_cookie_kwargs
from accounts.services.session import issue_refresh_token, logout_all_devices
from api.authentication import CookieJWTAuthentication


class SessionRevoked(APIException):
    """
    Raised when a refresh token's tv (token_version) claim is stale.

    Extends APIException directly (not AuthenticationFailed) so that DRF does
    not silently convert the 401 to 403 when authentication_classes = [].
    """

    status_code = 401
    default_detail = "Session has been revoked. Please log in again."
    default_code = "SESSION_REVOKED"
from carts.services.merge import merge_or_adopt_guest_cart, CartMergeStockConflict
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
    RegisterResponseSerializer,
    RefreshRequestSerializer,
    VerifyEmailRequestSerializer,
    VerifyEmailResponseSerializer,
    RequestEmailVerificationRequestSerializer,
    RequestEmailVerificationResponseSerializer,
)
from api.serializers.cart import CartMergeReportSerializer
from api.serializers.common import ErrorResponseSerializer
from api.serializers.password_reset import (
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from api.services.rate_limit import rate_limit_hit
from notifications.enqueue import enqueue_best_effort
from notifications.error_handler import NotificationErrorHandler
from notifications.exceptions import NotificationSendError

User = get_user_model()


class InvalidCredentials(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid email or password."
    default_code = "INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# Rate-limit constants — main auth endpoints
# Defaults are intentionally permissive; production values noted in comments.
# All limits can be overridden via Django settings (config/settings/).
# ---------------------------------------------------------------------------

# POST /auth/register/ — per-IP (anti-spam registration)
# Prod recommendation: 5/min per IP
_REGISTER_RL_PER_IP = int(getattr(settings, "REGISTER_RL_PER_IP", 5))
_REGISTER_RL_WINDOW_S = int(getattr(settings, "REGISTER_RL_WINDOW_S", 60))

# POST /auth/login/ — per-IP + per-email (credential brute-force)
# Prod recommendation: 10/min per IP; 5/10min per email
_LOGIN_RL_PER_IP = int(getattr(settings, "LOGIN_RL_PER_IP", 10))
_LOGIN_RL_WINDOW_S = int(getattr(settings, "LOGIN_RL_WINDOW_S", 60))
_LOGIN_RL_PER_EMAIL = int(getattr(settings, "LOGIN_RL_PER_EMAIL", 5))
_LOGIN_RL_PER_EMAIL_WINDOW_S = int(getattr(settings, "LOGIN_RL_PER_EMAIL_WINDOW_S", 600))

# POST /auth/refresh/ — per-IP (token replay / infra protection)
# Prod recommendation: 30/min per IP (refresh can be frequent under normal traffic)
_REFRESH_RL_PER_IP = int(getattr(settings, "REFRESH_RL_PER_IP", 30))
_REFRESH_RL_WINDOW_S = int(getattr(settings, "REFRESH_RL_WINDOW_S", 60))

# POST /auth/logout/ — per-IP (mild DoS protection)
# Prod recommendation: 30/min per IP
_LOGOUT_RL_PER_IP = int(getattr(settings, "LOGOUT_RL_PER_IP", 30))
_LOGOUT_RL_WINDOW_S = int(getattr(settings, "LOGOUT_RL_WINDOW_S", 60))


class RegisterView(APIView):
    authentication_classes = []  # allow unauthenticated
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Register user",
        request=RegisterRequestSerializer,
        responses={201: RegisterResponseSerializer},
    )
    def post(self, request):
        _rl_disabled = getattr(settings, "DISABLE_RATE_LIMITING_FOR_TESTS", False)
        ip = (
            (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
            or "unknown"
        )
        if not _rl_disabled:
            if rate_limit_hit(
                key=f"rl:register:ip:{ip}",
                limit=_REGISTER_RL_PER_IP,
                window_s=_REGISTER_RL_WINDOW_S,
            ):
                return Response(
                    {"detail": "Too many requests. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

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

        # Best-effort: send verification email after registration.
        # Registration must not fail if email dispatch fails.
        verification_email_sent = False
        if not getattr(user, "email_verified", False):
            try:
                raw_token = issue_email_verification_token(user)
                verification_url = (
                    f"{settings.PUBLIC_BASE_URL}"
                    f"/verify-email?token={raw_token}"
                )

                enqueue_best_effort(
                    "notifications.jobs.send_email_verification",
                    recipient_email=user.email,
                    verification_url=verification_url,
                )
                verification_email_sent = True
            except Exception:
                # Keep silent for the client; capture for observability.
                NotificationErrorHandler().capture()
                verification_email_sent = False

        # Serialize response with side-effect report field.
        setattr(user, "verification_email_sent", verification_email_sent)
        # NOTE: user.is_authenticated is a read-only property on AbstractBaseUser
        # that always returns True for an active user — no setattr needed.

        # Issue JWT tokens and set auth cookies — same as LoginView so the
        # client is immediately authenticated without a second round-trip.
        # tv claim embeds token_version for server-side revocation support.
        refresh_token = issue_refresh_token(user)
        access_str = str(refresh_token.access_token)
        refresh_str = str(refresh_token)

        # Adopt any guest cart present in the request (best-effort).
        cart_token = extract_cart_token(request)
        merge_or_adopt_guest_cart(user=user, raw_token=cart_token)

        response = Response(RegisterResponseSerializer(user).data, status=201)
        response.set_cookie(
            "cart_token", "", max_age=0, **cart_token_cookie_kwargs()
        )
        response.set_cookie(settings.AUTH_COOKIE_ACCESS, access_str, **auth_cookie_kwargs())
        response.set_cookie(settings.AUTH_COOKIE_REFRESH, refresh_str, **auth_cookie_kwargs())
        return response


class LoginView(APIView):
    authentication_classes = []  # allow unauthenticated
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login user (JWT)",
        description=(
            "Authenticate with email and password. Returns JWT access and refresh tokens "
            "as httpOnly cookies. "
            "Pass `remember_me=true` to extend the refresh token lifetime to "
            "AUTH_REFRESH_TTL_REMEMBER_SECONDS (default 30 days) instead of the "
            "standard AUTH_REFRESH_TTL_SECONDS (default 7 days). "
            "Access token lifetime is always 30 minutes regardless of this flag."
        ),
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
        _rl_disabled = getattr(settings, "DISABLE_RATE_LIMITING_FOR_TESTS", False)
        ip = (
            (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
            or "unknown"
        )
        if not _rl_disabled:
            raw_email = (request.data.get("email") or "").strip().lower()
            ip_limited = rate_limit_hit(
                key=f"rl:login:ip:{ip}",
                limit=_LOGIN_RL_PER_IP,
                window_s=_LOGIN_RL_WINDOW_S,
            )
            email_limited = bool(raw_email) and rate_limit_hit(
                key=f"rl:login:email:{raw_email}",
                limit=_LOGIN_RL_PER_EMAIL,
                window_s=_LOGIN_RL_PER_EMAIL_WINDOW_S,
            )
            if ip_limited or email_limited:
                return Response(
                    {"detail": "Too many requests. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            raise InvalidCredentials()

        # Determine refresh token lifetime based on remember_me flag.
        remember_me: bool = serializer.validated_data.get("remember_me", False)
        if remember_me:
            refresh_ttl: int = int(getattr(settings, "AUTH_REFRESH_TTL_REMEMBER_SECONDS", 30 * 24 * 3600))
        else:
            refresh_ttl = int(getattr(settings, "AUTH_REFRESH_TTL_SECONDS", 7 * 24 * 3600))

        # tv claim embeds token_version for server-side revocation support.
        refresh = issue_refresh_token(user, lifetime=timedelta(seconds=refresh_ttl))

        access_str = str(refresh.access_token)
        refresh_str = str(refresh)

        token_data = TokenResponseSerializer(
            {"access": access_str, "refresh": refresh_str}
        )

        response = Response(token_data.data, status=200)

        response.set_cookie(settings.AUTH_COOKIE_ACCESS, access_str, **auth_cookie_kwargs())
        # Set refresh cookie with the computed TTL so the browser honours
        # the remember-me duration via Max-Age.
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH,
            refresh_str,
            max_age=refresh_ttl,
            **auth_cookie_kwargs(),
        )

        return response


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def _get_authenticated_user_for_logout(self, request):
        """
        Best-effort JWT resolution for logout.

        Logout must stay idempotent even when cookies are already missing,
        expired, or malformed, so this helper never raises authentication
        errors. When a valid access or refresh token is present we resolve the
        user and let the logout endpoint revoke the session server-side.
        """
        authenticator = CookieJWTAuthentication()

        try:
            header = authenticator.get_header(request)
            if header is not None:
                raw_token = authenticator.get_raw_token(header)
                if raw_token is not None:
                    validated_token = authenticator.get_validated_token(raw_token)
                    return authenticator.get_user(validated_token)
        except Exception:
            pass

        refresh_cookie_name = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")
        refresh_str = request.COOKIES.get(refresh_cookie_name) or request.data.get("refresh")
        if not refresh_str:
            return None

        try:
            refresh_token = RefreshToken(refresh_str)
            user_id = refresh_token.get("user_id")
            if not user_id:
                return None

            user = User.objects.filter(pk=user_id).first()
            if user is None:
                return None

            tv_claim = refresh_token.get("tv")
            if tv_claim is not None and user.token_version != tv_claim:
                return None

            return user
        except Exception:
            return None

    def post(self, request):
        _rl_disabled = getattr(settings, "DISABLE_RATE_LIMITING_FOR_TESTS", False)
        ip = (
            (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
            or "unknown"
        )
        if not _rl_disabled:
            if rate_limit_hit(
                key=f"rl:logout:ip:{ip}",
                limit=_LOGOUT_RL_PER_IP,
                window_s=_LOGOUT_RL_WINDOW_S,
            ):
                return Response(
                    {"detail": "Too many requests. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        logout_user = self._get_authenticated_user_for_logout(request)
        if logout_user is not None:
            # The current JWT/session revocation primitive is token_version.
            # When a valid token is present, logout immediately invalidates any
            # stale access/refresh tokens that may still be replayed after the
            # browser cookie cleanup.
            logout_all_devices(logout_user)

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


def _check_token_version(refresh_str: str) -> None:
    """
    Decode the refresh token and validate the tv (token_version) claim.

    Raises AuthenticationFailed (HTTP 401) if the claim is stale — meaning
    the user has called logout-all or changed their email since the token
    was issued.

    If the token cannot be decoded (invalid / expired / blacklisted) this
    function returns silently — TokenRefreshSerializer will handle the error
    with the correct response shape.

    Tokens issued before tv support (no tv claim) are allowed through to
    preserve backward compatibility during a rolling deploy.
    """
    try:
        token_obj = RefreshToken(refresh_str)
        tv_claim = token_obj.get("tv")
        if tv_claim is None:
            # Legacy token without tv claim — allow for backward compatibility.
            return
        user_id = token_obj.get("user_id")
        user = User.objects.filter(pk=user_id).first()
        if user is None or user.token_version != tv_claim:
            raise SessionRevoked()
    except SessionRevoked:
        raise
    except Exception:
        # Token is structurally invalid, expired, or blacklisted.
        # Let TokenRefreshSerializer produce the proper error shape.
        return


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

        _rl_disabled = getattr(settings, "DISABLE_RATE_LIMITING_FOR_TESTS", False)
        ip = (
            (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
            or "unknown"
        )
        if not _rl_disabled:
            if rate_limit_hit(
                key=f"rl:refresh:ip:{ip}",
                limit=_REFRESH_RL_PER_IP,
                window_s=_REFRESH_RL_WINDOW_S,
            ):
                return Response(
                    {"detail": "Too many requests. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        # Validate token_version claim BEFORE standard refresh validation.
        # This rejects sessions revoked via logout-all even if the token is
        # otherwise cryptographically valid.
        _check_token_version(refresh_str)

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
        except SessionRevoked:
            raise  # already 401 — do not swallow
        except AuthenticationFailed:
            raise  # already 401 — do not swallow
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


# ---------------------------------------------------------------------------
# Password-reset flow
# ---------------------------------------------------------------------------

_PW_RESET_REQUEST_RL_PER_IP = int(getattr(settings, "PW_RESET_REQUEST_RL_PER_IP", 10))
_PW_RESET_REQUEST_RL_WINDOW_S = int(getattr(settings, "PW_RESET_REQUEST_RL_WINDOW_S", 3600))
_PW_RESET_CONFIRM_RL_PER_IP = int(getattr(settings, "PW_RESET_CONFIRM_RL_PER_IP", 20))
_PW_RESET_CONFIRM_RL_WINDOW_S = int(getattr(settings, "PW_RESET_CONFIRM_RL_WINDOW_S", 3600))


@extend_schema(tags=["Auth"])
class PasswordResetRequestView(APIView):
    """
    Initiate a password-reset flow.

    Anti-enumeration: always responds 204 regardless of whether the email
    is registered.  If it exists, a single-use reset link is sent by email.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Request a password reset",
        description=(
            "Sends a password-reset link to the provided email address. "
            "Always returns 204 to prevent email enumeration. "
            "The link points to the frontend reset page and expires in 60 minutes."
        ),
        request=PasswordResetRequestSerializer,
        responses={
            204: OpenApiResponse(description="Request accepted (email sent if address is registered)."),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Validation error (e.g. invalid email format).",
            ),
            429: OpenApiResponse(description="Too many requests. Try again later."),
        },
    )
    def post(self, request):
        _rl_disabled = getattr(settings, "DISABLE_RATE_LIMITING_FOR_TESTS", False)
        ip = (
            (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
            or "unknown"
        )
        if not _rl_disabled:
            if rate_limit_hit(
                key=f"rl:pw_reset_request:ip:{ip}",
                limit=_PW_RESET_REQUEST_RL_PER_IP,
                window_s=_PW_RESET_REQUEST_RL_WINDOW_S,
            ):
                return Response(
                    {"detail": "Too many requests. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from accounts.services.password_reset import request_password_reset
        request_password_reset(serializer.validated_data["email"])

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Auth"])
class PasswordResetConfirmView(APIView):
    """
    Confirm a password reset using a single-use token.

    Validates the token, applies the new password, revokes all active sessions
    (token_version++), and marks the token as used.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Confirm password reset",
        description=(
            "Validates the single-use reset token and sets the new password. "
            "On success all active sessions are invalidated and the user must "
            "log in again. The token is marked used and cannot be replayed."
        ),
        request=PasswordResetConfirmSerializer,
        responses={
            204: OpenApiResponse(description="Password reset successfully."),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description=(
                    "Validation error: invalid/expired/used token, "
                    "confirmation mismatch, or weak password."
                ),
            ),
            429: OpenApiResponse(description="Too many requests. Try again later."),
        },
    )
    def post(self, request):
        _rl_disabled = getattr(settings, "DISABLE_RATE_LIMITING_FOR_TESTS", False)
        ip = (
            (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
            or "unknown"
        )
        if not _rl_disabled:
            if rate_limit_hit(
                key=f"rl:pw_reset_confirm:ip:{ip}",
                limit=_PW_RESET_CONFIRM_RL_PER_IP,
                window_s=_PW_RESET_CONFIRM_RL_WINDOW_S,
            ):
                return Response(
                    {"detail": "Too many requests. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from accounts.services.password_reset import confirm_password_reset
        confirm_password_reset(
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Post-login settling endpoints
# These are intentionally separate from LoginView so that login remains a
# pure authentication step (fast, no domain side-effects).
# Clients call these once after a successful login / page load.
# ---------------------------------------------------------------------------


class CartMergeView(APIView):
    """
    Merge a guest (anonymous) cart into the authenticated user's active cart.

    Idempotent: safe to call multiple times with the same guest token.
    Clears the cart_token cookie on success so the browser no longer sends
    the stale guest token.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Cart"],
        summary="Merge guest cart into authenticated user's cart",
        description=(
            "Merges or adopts the anonymous guest cart identified by the "
            "cart_token cookie / X-Cart-Token header into the authenticated "
            "user's active cart. Always returns 200 with a full merge report. "
            "If there is no guest token, result is NOOP and performed=false. "
            "Quantities exceeding available stock are capped and reported as "
            "STOCK_ADJUSTED warnings instead of causing an error. "
            "The cart_token cookie is cleared when a token was processed."
        ),
        request=None,
        responses={
            200: CartMergeReportSerializer,
            401: OpenApiResponse(description="Authentication required."),
        },
        examples=[
            OpenApiExample(
                name="NOOP — no guest token",
                value={
                    "performed": False,
                    "result": "NOOP",
                    "items_added": 0,
                    "items_updated": 0,
                    "items_removed": 0,
                    "warnings": [],
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                name="MERGED with stock adjustment",
                value={
                    "performed": True,
                    "result": "MERGED",
                    "items_added": 0,
                    "items_updated": 1,
                    "items_removed": 0,
                    "warnings": [{"code": "STOCK_ADJUSTED", "product_id": 5, "requested": 3, "applied": 1}],
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        cart_token = extract_cart_token(request)

        if not cart_token:
            # No guest token present — return NOOP report immediately.
            # Do not touch the campaign offer cookie for NOOP.
            from carts.services.merge import _noop_report
            report = _noop_report()
            return Response(CartMergeReportSerializer(report).data, status=status.HTTP_200_OK)

        # merge_or_adopt_guest_cart caps stock and returns a full report (no 409).
        report = merge_or_adopt_guest_cart(user=request.user, raw_token=cart_token)

        response = Response(CartMergeReportSerializer(report).data, status=status.HTTP_200_OK)
        # Clear the guest cart cookie so the browser stops sending the old token.
        response.set_cookie(
            "cart_token",
            "",
            max_age=0,
            **cart_token_cookie_kwargs(),
        )

        # Sync the campaign offer cookie to the merge winner so the browser
        # always carries the best valid offer after a guest→auth merge.
        # Only applied when a merge was actually performed (ADOPTED or MERGED);
        # NOOP short-circuits above and never reaches this point.
        if report["performed"]:
            from api.services.campaign_offer_session import (  # noqa: PLC0415
                set_campaign_offer_cookie as _set_offer_cookie,
                clear_campaign_offer_cookie as _clear_offer_cookie,
            )
            winning_token = report.get("winning_offer_token")
            if winning_token:
                _set_offer_cookie(response, winning_token)
            else:
                # Neither cart had a valid campaign offer — clear any stale cookie
                # so the browser does not carry an expired/invalid token.
                _clear_offer_cookie(response)

        return response


class OrdersClaimView(APIView):
    """
    Claim any guest orders whose contact email matches the authenticated user's
    verified email address.

    Safe to call multiple times — the underlying service is idempotent.
    Requires a verified email; returns claimed_orders=0 for unverified accounts.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Orders"],
        summary="Claim guest orders for the authenticated user",
        description=(
            "Finds previously placed guest orders whose contact email matches "
            "the authenticated user's verified email and assigns them to the user. "
            "If the user's email is not verified, returns claimed_orders=0 without "
            "performing any database writes. Safe to call multiple times."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                description="Number of orders claimed (may be 0).",
            ),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request):
        if not getattr(request.user, "email_verified", False):
            return Response({"claimed_orders": 0}, status=status.HTTP_200_OK)

        claimed = claim_guest_orders_for_user(request.user)
        return Response({"claimed_orders": claimed}, status=status.HTTP_200_OK)
