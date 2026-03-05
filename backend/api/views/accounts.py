from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.account import AccountSerializer
from api.serializers.change_email import ChangeEmailSerializer
from api.serializers.change_password import ChangePasswordSerializer
from api.serializers.common import ErrorResponseSerializer
from api.services.rate_limit import rate_limit_hit
from accounts.services.email_change import (
    cancel_email_change,
    confirm_email_change,
    request_email_change,
)
from accounts.services.session import logout_all_devices
from notifications.jobs import send_password_change_notification


@extend_schema(tags=["Account"])
class AccountView(GenericAPIView):
    """
    Self-service account identity endpoint.

    Allows the authenticated user to read and partially update their own
    identity fields (first_name, last_name). Email changes are rejected here;
    they require a separate reverification flow.
    """

    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get own account",
        description=(
            "Returns the identity fields for the currently authenticated user: "
            "email (read-only), first_name, last_name, and email_verified (read-only)."
        ),
        responses={
            200: AccountSerializer,
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Update own account",
        description=(
            "Partially updates the authenticated user's identity. "
            "Only first_name and last_name may be changed. "
            "Supplying `email` in the request body returns HTTP 400."
        ),
        request=AccountSerializer,
        responses={
            200: AccountSerializer,
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Validation error — e.g. email change is not allowed via this endpoint.",
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Email-change flow  (ADR-035)
# ---------------------------------------------------------------------------

_CHANGE_EMAIL_RL_PER_USER = int(
    getattr(settings, "CHANGE_EMAIL_RL_PER_USER", 5)
)
_CHANGE_EMAIL_RL_PER_IP = int(
    getattr(settings, "CHANGE_EMAIL_RL_PER_IP", 20)
)
_CHANGE_EMAIL_RL_WINDOW_S = int(
    getattr(settings, "CHANGE_EMAIL_RL_WINDOW_S", 3600)
)


@extend_schema(tags=["Account"])
class ChangeEmailView(APIView):
    """
    Initiate a secure email-change flow.

    Creates a pending EmailChangeRequest linked to the authenticated user.
    Two emails are sent (best-effort):
    - A confirmation link to the *new* email address.
    - A security notification with a one-click cancel link to the *old* address.

    Invariant: at most one active request per user — a new request automatically
    cancels any previous active request.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Request email address change",
        description=(
            "Initiates the email-change flow. "
            "The new address is not applied until the confirmation link is clicked. "
            "Requires the current password to prevent account takeover. "
            "Throttled per user and per IP."
        ),
        request=ChangeEmailSerializer,
        responses={
            204: OpenApiResponse(description="Email-change request created."),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description=(
                    "Validation error: email mismatch, email already in use, "
                    "or invalid current password."
                ),
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
        },
    )
    def post(self, request):
        user = request.user

        # Per-user + per-IP rate limiting (anti-spam / brute-force protection).
        # Rate limiting is skipped in test environments
        # (when STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS is True).
        _testing = getattr(settings, "STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS", False)
        ip = (
            (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
            or "unknown"
        )
        if not _testing:
            user_limited = rate_limit_hit(
                key=f"rl:change_email:user:{user.pk}",
                limit=_CHANGE_EMAIL_RL_PER_USER,
                window_s=_CHANGE_EMAIL_RL_WINDOW_S,
            )
            ip_limited = rate_limit_hit(
                key=f"rl:change_email:ip:{ip}",
                limit=_CHANGE_EMAIL_RL_PER_IP,
                window_s=_CHANGE_EMAIL_RL_WINDOW_S,
            )
            if user_limited or ip_limited:
                return Response(
                    {"detail": "Too many requests. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        serializer = ChangeEmailSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:512] or None

        request_email_change(
            user,
            new_email=serializer.validated_data["new_email"],
            current_password=serializer.validated_data["current_password"],
            request_ip=ip,
            user_agent=user_agent,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Account"])
class ConfirmEmailChangeView(APIView):
    """
    Confirm a pending email-change request via a one-time token.

    The token is delivered to the *new* email address as part of the flow
    initiated by POST /api/v1/account/change-email/.

    On success:
    - The user's email is updated to the new address.
    - email_verified is set to True.
    - All active JWT tokens for the user are blacklisted (logout-all).
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Confirm email address change",
        description=(
            "Validates the single-use confirmation token and applies the pending "
            "email change. After a successful confirmation all existing sessions "
            "are invalidated and the user must log in again with the new address."
        ),
        parameters=[
            OpenApiParameter(
                name="token",
                location=OpenApiParameter.QUERY,
                required=True,
                description="Single-use confirmation token received via email.",
                type=str,
            )
        ],
        responses={
            204: OpenApiResponse(description="Email changed successfully."),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Token is invalid, expired, already used, or the request was cancelled.",
            ),
        },
    )
    def get(self, request):
        raw_token = request.query_params.get("token", "")
        confirm_email_change(raw_token)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Account"])
class CancelEmailChangeView(APIView):
    """
    Cancel a pending email-change request via a one-time cancel token.

    The cancel token is sent to the *old* email address as a one-click security
    action. Cancellation prevents the confirmation from succeeding.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Cancel email address change",
        description=(
            "Validates the single-use cancel token and cancels the pending "
            "email-change request, preventing any subsequent confirmation."
        ),
        parameters=[
            OpenApiParameter(
                name="token",
                location=OpenApiParameter.QUERY,
                required=True,
                description="Single-use cancel token received via the security notification email.",
                type=str,
            )
        ],
        responses={
            204: OpenApiResponse(description="Email-change request cancelled."),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Token is invalid, expired, already used, or the request was already confirmed.",
            ),
        },
    )
    def get(self, request):
        raw_token = request.query_params.get("token", "")
        cancel_email_change(raw_token)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Account"])
class LogoutAllView(APIView):
    """
    Revoke all active sessions for the authenticated user.

    Increments token_version on the user record so that every previously
    issued refresh token is rejected on its next use.  The current device's
    auth cookies are also cleared as a convenience.

    Typical callers:
    - "Log out of all devices" UI action.
    - Automated revocation after a security-sensitive change (email change,
      password change, suspicious activity detection).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Log out from all devices",
        description=(
            "Increments the user's token_version, immediately invalidating every "
            "outstanding refresh token.  Auth cookies for the current request are "
            "also deleted.  Access tokens already in flight remain valid until "
            "their natural expiry (typically 30 minutes).\n\n"
            "Use this endpoint after a password or email change, or to force "
            "global session revocation on suspected account compromise."
        ),
        responses={
            204: OpenApiResponse(description="All sessions revoked successfully."),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided or are invalid.",
            ),
        },
    )
    def post(self, request):
        logout_all_devices(request.user)

        # Clear cookies on the current device as well.
        access_cookie = getattr(settings, "AUTH_COOKIE_ACCESS", "access_token")
        refresh_cookie = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")
        cookie_path = getattr(settings, "AUTH_COOKIE_PATH", "/")

        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(access_cookie, path=cookie_path)
        response.delete_cookie(refresh_cookie, path=cookie_path)
        return response


@extend_schema(tags=["Account"])
class ChangePasswordView(APIView):
    """
    Change the authenticated user's password.

    Validates the current password, applies the change, and revokes all
    active sessions (token_version++) so existing refresh tokens become
    immediately invalid.  The current device's auth cookies are also cleared.

    A best-effort security notification is sent to the account email address.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change account password",
        description=(
            "Changes the authenticated user's password.  "
            "Requires the current password for verification.  "
            "On success all active sessions are revoked (logout-all) and the "
            "caller must re-authenticate with the new credentials.  "
            "A security notification is sent to the account email (best-effort)."
        ),
        request=ChangePasswordSerializer,
        responses={
            204: OpenApiResponse(description="Password changed and all sessions revoked."),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description=(
                    "Validation error: incorrect current password, "
                    "confirmation mismatch, or weak new password."
                ),
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided or are invalid.",
            ),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_password = serializer.validated_data["new_password"]

        # Apply the new password.
        user.set_password(new_password)
        user.save(update_fields=["password"])

        # Revoke all sessions — increments token_version so any outstanding
        # refresh token is rejected on its next use.
        logout_all_devices(user)

        # Send security notification (best-effort — never blocks the response).
        send_password_change_notification(recipient_email=user.email)

        # Clear cookies on the current device so the browser is also signed out.
        access_cookie = getattr(settings, "AUTH_COOKIE_ACCESS", "access_token")
        refresh_cookie = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")
        cookie_path = getattr(settings, "AUTH_COOKIE_PATH", "/")

        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(access_cookie, path=cookie_path)
        response.delete_cookie(refresh_cookie, path=cookie_path)
        return response
