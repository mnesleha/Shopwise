from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.serializers.account import AccountSerializer
from api.serializers.common import ErrorResponseSerializer


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
