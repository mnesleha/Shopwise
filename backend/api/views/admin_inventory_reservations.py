from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ReadOnlyModelViewSet

from drf_spectacular.utils import extend_schema, extend_schema_view

from orders.models import InventoryReservation
from api.serializers.admin_inventory_reservation import (
    InventoryReservationAdminSerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=["Admin"],
        summary="List inventory reservations",
    ),
    retrieve=extend_schema(
        tags=["Admin"],
        summary="Retrieve inventory reservation",
    ),
)
class InventoryReservationAdminViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = InventoryReservation.objects.all()
    serializer_class = InventoryReservationAdminSerializer
