from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.filters import OrderingFilter
from django.utils import timezone
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from orders.models import InventoryReservation
from api.serializers.admin_inventory_reservation import (
    InventoryReservationAdminSerializer,
)


class InventoryReservationFilter(filters.FilterSet):
    overdue = filters.BooleanFilter(method="filter_overdue")

    def filter_overdue(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            status=InventoryReservation.Status.ACTIVE,
            expires_at__lt=timezone.now(),
        )

    class Meta:
        model = InventoryReservation
        fields = ["order", "product", "status", "release_reason"]


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

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = InventoryReservationFilter

    ordering = ["-created_at"]
    ordering_fields = ["created_at", "expires_at", "status", "quantity"]
