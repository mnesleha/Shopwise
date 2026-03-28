from django.http import Http404

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.common import ErrorResponseSerializer
from api.serializers.tracking import PublicTrackingResponseSerializer
from shipping.models import Shipment


@extend_schema(
    tags=["Shipping"],
    summary="Retrieve public shipment tracking",
    description=(
        "Returns a provider-agnostic shipment tracking summary by tracking number. "
        "The response is intentionally limited to shipment-facing data only."
    ),
    responses={
        200: PublicTrackingResponseSerializer,
        404: OpenApiResponse(response=ErrorResponseSerializer, description="Tracking number not found."),
    },
)
class PublicTrackingRetrieveView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, tracking_number: str):
        shipment = (
            Shipment.objects.prefetch_related("events")
            .filter(tracking_number=tracking_number)
            .order_by("-created_at")
            .first()
        )
        if shipment is None:
            raise Http404()

        payload = {
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "carrier_name": shipment.carrier_name_snapshot,
            "service_name": shipment.service_name_snapshot,
            "shipment_timeline": shipment.get_timeline(),
        }
        return Response(PublicTrackingResponseSerializer(payload).data, status=200)