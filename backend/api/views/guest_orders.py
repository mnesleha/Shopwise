from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from api.serializers.order import OrderResponseSerializer
from orders.services.guest_order_access_service import GuestOrderAccessService


@extend_schema(
    tags=["Guest Orders"],
    summary="Retrieve a guest order (token-based, read-only)",
    description=(
        "Read-only access to a guest order using a capability token. "
        "Returns 404 for any invalid token or non-guest order to avoid information leakage."
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
        return Response(OrderResponseSerializer(order).data, status=200)
