from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiExample
from api.serializers.common import ErrorResponseSerializer
from discounts.models import Discount
from api.serializers.discount import DiscountSerializer
from django.utils.timezone import now


@extend_schema_view(
    list=extend_schema(
        tags=["Discounts"],
        summary="List active discounts",
        description="""
Returns currently active discounts.

Only discounts that:
- are active
- are within their validity period
- target a product

are returned.

Notes:
- Discounts are read-only.
- Discounts do not calculate final prices.
""",
        responses={
            200: DiscountSerializer,
        },
        examples=[
            OpenApiExample(
                name="Active product discount",
                value=[
                    {
                        "id": 1,
                        "discount_type": "PERCENT",
                        "value": "10.00",
                        "product": {
                            "id": 42,
                            "name": "Wireless Mouse"
                        }
                    }
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["Discounts"],
        summary="Retrieve discount detail",
        description="""
Returns details of a single discount.

Notes:
- Only active discounts within their validity period are accessible.
- Discounts are read-only.
""",
        responses={
            200: DiscountSerializer,
            404: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Discount detail",
                value={
                    "id": 1,
                    "discount_type": "FIXED",
                    "value": "5.00",
                    "product": {
                        "id": 42,
                        "name": "Wireless Mouse"
                    }
                },
                response_only=True,
            ),
        ],
    ),
)
class DiscountViewSet(ReadOnlyModelViewSet):
    serializer_class = DiscountSerializer

    def get_queryset(self):
        today = now().date()
        return Discount.objects.filter(
            is_active=True,
            valid_from__lte=today,
            valid_to__gte=today,
        ).select_related("product")
