from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
)
from orders.models import Order
from api.serializers.order import OrderResponseSerializer
from api.serializers.common import ErrorResponseSerializer


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
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
