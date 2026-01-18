from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from accounts.permissions import (
    ORDERS_CAN_FULFILL,
    ORDERS_CAN_CANCEL_ADMIN,
)
from api.permissions import require_staff_or_perm
from api.serializers.order import OrderResponseSerializer
from orders.models import Order
from orders.services.order_service import OrderService


@extend_schema_view(
    ship=extend_schema(tags=["Admin"], summary="Ship an order"),
    deliver=extend_schema(tags=["Admin"], summary="Deliver an order"),
    cancel=extend_schema(tags=["Admin"], summary="Cancel an order (admin)"),
)
class AdminOrderViewSet(GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderResponseSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    @action(
        detail=True,
        methods=["post"],
        url_path="ship",
        permission_classes=[require_staff_or_perm(ORDERS_CAN_FULFILL)],
    )
    def ship(self, request, pk=None):
        order = self.get_object()
        order = OrderService.ship_by_admin(order=order, actor_user=request.user)
        return Response(self.get_serializer(order).data, status=200)

    @action(
        detail=True,
        methods=["post"],
        url_path="deliver",
        permission_classes=[require_staff_or_perm(ORDERS_CAN_FULFILL)],
    )
    def deliver(self, request, pk=None):
        order = self.get_object()
        order = OrderService.deliver_by_admin(order=order, actor_user=request.user)
        return Response(self.get_serializer(order).data, status=200)

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
        permission_classes=[require_staff_or_perm(ORDERS_CAN_CANCEL_ADMIN)],
    )
    def cancel(self, request, pk=None):
        order = self.get_object()
        order = OrderService.cancel_by_admin(order=order, actor_user=request.user)
        return Response(self.get_serializer(order).data, status=200)
