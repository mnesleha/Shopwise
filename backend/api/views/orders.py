from requests import request
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiResponse,
)
from orders.models import Order
from api.serializers.order import OrderResponseSerializer
from api.serializers.common import ErrorResponseSerializer
from orders.services.order_service import OrderService
from auditlog.models import AuditEvent
from auditlog.actions import AuditActions
from auditlog.services import AuditService


@extend_schema_view(
    list=extend_schema(
        tags=["Orders"],
        summary="List user orders",
        description="""
Returns a list of orders belonging to the authenticated user.

Orders represent completed checkout results and are read-only.

Notes:
- Orders are immutable.
- Orders are created exclusively via cart checkout.
- The list is ordered by creation time (implicit database order).
""",
        responses={
            200: OrderResponseSerializer,
            401: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="List of orders",
                value=[
                    {
                        "id": 123,
                        "status": "CREATED",
                        "items": [
                            {
                                "id": 1,
                                "product": 42,
                                "quantity": 2,
                                "unit_price": "25.00",
                                "line_total": "40.00",
                                "discount": {
                                    "type": "PERCENT",
                                    "value": "20.00"
                                }
                            }
                        ],
                        "total": "40.00"
                    }
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["Orders"],
        summary="Retrieve order detail",
        description="""
Returns details of a specific order.

Notes:
- Only orders belonging to the authenticated user are accessible.
- Orders cannot be modified after creation.
""",
        responses={
            200: OrderResponseSerializer,
            401: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Order detail",
                value={
                    "id": 123,
                    "status": "PAID",
                    "items": [
                        {
                            "id": 1,
                            "product": 42,
                            "quantity": 2,
                            "unit_price": "25.00",
                            "line_total": "40.00",
                            "discount": {
                                "type": "PERCENT",
                                "value": "20.00"
                            }
                        }
                    ],
                    "total": "40.00"
                },
                response_only=True,
            ),
        ],
    ),
)
class OrderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    queryset = Order.objects.all()
    serializer_class = OrderResponseSerializer
    http_method_names = ["post", "get", "head", "options"]

    def initial(self, request, *args, **kwargs):
        """Runs before authentication and permissions - perfect for debugging"""
        print("=" * 80)
        print("DEBUG OrderViewSet.initial() - BEFORE AUTH")
        print("All COOKIES:", dict(request.COOKIES))
        print("HAS access_token:", "access_token" in request.COOKIES)
        print("HAS refresh_token:", "refresh_token" in request.COOKIES)
        print("Authorization header:", request.META.get('HTTP_AUTHORIZATION', 'NOT SET'))
        print("Available authenticators:", [a.__class__.__name__ for a in self.get_authenticators()])
        print("HTTP_COOKIE header:", request.META.get("HTTP_COOKIE", "NOT SET"))
        print("=" * 80)
        
        super().initial(request, *args, **kwargs)
        
        print("=" * 80)
        print("DEBUG OrderViewSet.initial() - AFTER AUTH")
        print("request.user:", request.user)
        print("request.user.is_authenticated:", request.user.is_authenticated)
        print("Successful authenticator:", request.successful_authenticator.__class__.__name__ if hasattr(request, 'successful_authenticator') and request.successful_authenticator else "NONE")
        print("HTTP_COOKIE header:", request.META.get("HTTP_COOKIE", "NOT SET"))
        print("=" * 80)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Prevent direct order creation. Orders must be created via checkout only.
        raise MethodNotAllowed("POST")

    @extend_schema(
        summary="Cancel an order",
        description=(
            "Cancels a customer's own order if it is still in CREATED state. "
            "This releases ACTIVE inventory reservations and transitions the order to CANCELLED "
            "with cancel_reason=CUSTOMER_REQUEST."
        ),
        responses={
            200: OrderResponseSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Order not found"),
            409: OpenApiResponse(description="Invalid order state"),
        },
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "id": 123,
                    "status": "CANCELLED",
                    "cancel_reason": "CUSTOMER_REQUEST",
                    "cancelled_by": "CUSTOMER",
                    "cancelled_at": "2026-01-14T12:00:00Z",
                },
                response_only=True,
            ),
            OpenApiExample(
                "Invalid state",
                value={"code": "INVALID_ORDER_STATE",
                       "message": "...", "errors": {}},
                response_only=True,
                status_codes=["409"],
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        order = self.get_object()

        order = OrderService.cancel_by_customer(
            order=order,
            actor_user=request.user,
        )

        # Best-effort audit logging: cancellation must not fail the business flow.
        AuditService.emit(
            entity_type="order",
            entity_id=str(order.id),
            action=AuditActions.ORDER_CANCELLED,
            actor_type=AuditEvent.ActorType.CUSTOMER,
            actor_user=request.user,
            metadata={
                "cancel_reason": order.cancel_reason,
                "cancelled_by": order.cancelled_by,
            },
            fail_silently=True,
        )

        data = self.get_serializer(order).data
        data.update(
            {
                "cancel_reason": order.cancel_reason,
                "cancelled_by": order.cancelled_by,
                "cancelled_at": order.cancelled_at,
            }
        )
        return Response(data, status=200)
