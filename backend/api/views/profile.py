from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from accounts.models import Address, CustomerProfile
from api.serializers.profile import AddressSerializer, CustomerProfileSerializer
from api.serializers.common import ErrorResponseSerializer


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@extend_schema(tags=["Profile"])
class ProfileView(GenericAPIView):
    """
    Retrieve or partially update the authenticated user's CustomerProfile.
    """

    serializer_class = CustomerProfileSerializer
    permission_classes = [IsAuthenticated]

    def _get_profile(self):
        profile, _ = CustomerProfile.objects.get_or_create(user=self.request.user)
        return profile

    @extend_schema(
        summary="Get own profile",
        description=(
            "Returns the CustomerProfile for the currently authenticated user. "
            "The profile is auto-created on first access if it does not exist yet."
        ),
        responses={
            200: CustomerProfileSerializer,
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        profile = self._get_profile()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @extend_schema(
        summary="Update own profile defaults",
        description=(
            "Partially updates the authenticated user's CustomerProfile. "
            "Use this endpoint to set or clear default shipping/billing addresses. "
            "The supplied address IDs must belong to the authenticated user."
        ),
        responses={
            200: CustomerProfileSerializer,
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description=(
                    "Validation error: the supplied address does not belong "
                    "to this user's profile."
                ),
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        profile = self._get_profile()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(
        tags=["Addresses"],
        summary="List own addresses",
        description=(
            "Returns all addresses belonging to the authenticated user. "
            "Results are not paginated."
        ),
        responses={
            200: AddressSerializer(many=True),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
        },
    ),
    create=extend_schema(
        tags=["Addresses"],
        summary="Create address",
        description=(
            "Creates a new address for the authenticated user. "
            "The `profile` ownership is set server-side and cannot be overridden "
            "via the request payload."
        ),
        responses={
            201: AddressSerializer,
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Validation error.",
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
        },
    ),
    retrieve=extend_schema(
        tags=["Addresses"],
        summary="Retrieve address",
        description="Returns a single address owned by the authenticated user.",
        responses={
            200: AddressSerializer,
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
            404: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Address not found or does not belong to this user.",
            ),
        },
    ),
    partial_update=extend_schema(
        tags=["Addresses"],
        summary="Update address",
        description="Partially updates an address owned by the authenticated user.",
        responses={
            200: AddressSerializer,
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Validation error.",
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
            404: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Address not found or does not belong to this user.",
            ),
        },
    ),
    destroy=extend_schema(
        tags=["Addresses"],
        summary="Delete address",
        description=(
            "Deletes an address owned by the authenticated user. "
            "If the address was set as a default on the profile, those defaults "
            "will be set to null automatically."
        ),
        responses={
            204: OpenApiResponse(description="Address deleted successfully."),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication credentials were not provided.",
            ),
            404: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Address not found or does not belong to this user.",
            ),
        },
    ),
)
class AddressViewSet(ModelViewSet):
    """
    CRUD for addresses owned by the authenticated user.
    Full update (PUT) is not exposed; use PATCH for partial updates.
    """

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        profile, _ = CustomerProfile.objects.get_or_create(user=self.request.user)
        return Address.objects.filter(profile=profile)

    def perform_create(self, serializer):
        profile, _ = CustomerProfile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)
