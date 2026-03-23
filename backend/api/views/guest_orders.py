import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.http import Http404
from django.conf import settings

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.guest_bootstrap import (
    GuestBootstrapRequestSerializer,
    GuestBootstrapResponseSerializer,
)
from api.serializers.order import OrderResponseSerializer
from config.settings.base import auth_cookie_kwargs
from accounts.services.session import issue_refresh_token
from orders.services.bootstrap import seed_addresses_from_order
from orders.services.claim import claim_guest_orders_for_user
from orders.services.guest_order_access_service import GuestOrderAccessService

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Guest Orders"],
    summary="Retrieve a guest order (token-based, read-only)",
    description=(
        "Read-only access to a guest order using a capability token. "
        "Returns 404 for any invalid token or non-guest order to avoid information leakage. "
        "The response includes `email_account_exists` which indicates whether the order's "
        "contact email is already registered as a full account."
    ),
    parameters=[
        OpenApiParameter(
            name="token",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Guest access token.",
        ),
    ],
    responses={200: OrderResponseSerializer},
)
class GuestOrderRetrieveView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, order_id: int):
        token = request.query_params.get("token")
        order = GuestOrderAccessService.validate(
            order_id=order_id,
            token=token,
        )
        if order is None:
            raise Http404()

        data = dict(OrderResponseSerializer(order).data)
        # Indicate whether the order email already has a registered account.
        # Used by the frontend to decide whether to show the create-account CTA
        # or an existing-account prompt.  Not a security risk here because the
        # caller proved ownership of the email by possessing the guest access token.
        data["email_account_exists"] = User.objects.filter(
            email=order.customer_email_normalized
        ).exists()

        return Response(data, status=200)


@extend_schema(
    tags=["Guest Orders"],
    summary="Bootstrap a full account from a verified guest order",
    description=(
        "Creates a new registered account using the identity data already present in a "
        "verified guest order (email, name). Only a password is required as input. "
        "On success the account is created, profile addresses are seeded from the order "
        "snapshot (best-effort), all guest orders with the same email are claimed, and the "
        "user is logged in (JWT cookies set). "
        "Returns 404 for invalid/missing tokens. "
        "Returns 409 if the email is already registered."
    ),
    parameters=[
        OpenApiParameter(
            name="token",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Guest access token.",
        ),
    ],
    request=GuestBootstrapRequestSerializer,
    responses={
        201: GuestBootstrapResponseSerializer,
        404: OpenApiResponse(description="Invalid or missing guest access token."),
        409: OpenApiResponse(description="Email already registered — use the login flow."),
    },
)
class GuestOrderBootstrapView(APIView):
    """
    Convert a verified guest order into a full account.

    The endpoint is intentionally minimal: only a password is required because
    all other identity data (email, name) is already available from the verified
    order snapshot.  Gated behind the same capability token as the read-only
    guest order view — only the verified email owner can trigger account creation.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, order_id: int):
        token = request.query_params.get("token")
        order = GuestOrderAccessService.validate(
            order_id=order_id,
            token=token,
        )
        if order is None:
            raise Http404()

        serializer = GuestBootstrapRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = order.customer_email_normalized

        # Existing-account guard — do not create a duplicate.
        if User.objects.filter(email=email).exists():
            return Response(
                {
                    "code": "EMAIL_ALREADY_REGISTERED",
                    "detail": (
                        "An account with this email already exists. "
                        "Please log in to access your orders."
                    ),
                },
                status=409,
            )

        password = serializer.validated_data["password"]

        # Derive first/last name from shipping snapshot.
        name_parts = (order.shipping_name or "").strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    # The guest access token proves email ownership (the token
                    # was sent to this address when the order was placed), so
                    # we mark the email as verified immediately.
                    email_verified=True,
                )
        except IntegrityError:
            # Race-condition safety net.
            return Response(
                {
                    "code": "EMAIL_ALREADY_REGISTERED",
                    "detail": (
                        "An account with this email already exists. "
                        "Please log in to access your orders."
                    ),
                },
                status=409,
            )

        # Best-effort: seed profile addresses from order snapshot.
        # The service catches its own exceptions, but we add an outer guard
        # here so that any unexpected raise (e.g. from mocked code in tests)
        # also cannot roll back the account creation.
        try:
            seed_addresses_from_order(user=user, order=order)
        except Exception:
            logger.exception(
                "Address seeding raised unexpectedly for user %s (order %s)",
                user.pk,
                order.pk,
            )

        # Claim all guest orders with the same verified email (idempotent).
        # email_verified=True is set above so the service will process them.
        try:
            claim_guest_orders_for_user(user)
        except Exception:
            logger.exception(
                "Guest order claim failed after bootstrap for user %s", user.pk
            )

        # Issue JWT tokens and set httpOnly auth cookies — same pattern as
        # LoginView / RegisterView.
        refresh_token = issue_refresh_token(user)
        access_str = str(refresh_token.access_token)
        refresh_str = str(refresh_token)

        response = Response(GuestBootstrapResponseSerializer(user).data, status=201)
        response.set_cookie(
            settings.AUTH_COOKIE_ACCESS, access_str, **auth_cookie_kwargs()
        )
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH, refresh_str, **auth_cookie_kwargs()
        )
        return response
