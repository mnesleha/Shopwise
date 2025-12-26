from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from api.serializers.common import ErrorResponseSerializer
from products.models import Product
from api.serializers.product import ProductSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Products"],
        summary="List available products",
        description="""
Returns a list of products available for purchase.

Only products that are:
- active
- in stock (stock_quantity > 0)

are returned by this endpoint.

Notes:
- Products are read-only.
- Stock quantity is informational and does not represent reservation.
""",
        responses={
            200: ProductSerializer,
        },
        examples=[
            OpenApiExample(
                name="List of products",
                value=[
                    {
                        "id": 1,
                        "name": "Wireless Mouse",
                        "price": "29.99",
                        "stock_quantity": 15
                    }
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["Products"],
        summary="Retrieve product detail",
        description="""
Returns details of a single product.

The product must be:
- active
- in stock

Otherwise, it will not be accessible via the API.
""",
        responses={
            200: ProductSerializer,
            404: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Product detail",
                value={
                    "id": 1,
                    "name": "Wireless Mouse",
                    "price": "29.99",
                    "stock_quantity": 15
                },
                response_only=True,
            ),
        ],
    ),
)
class ProductViewSet(ReadOnlyModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(
            is_active=True,
            stock_quantity__gt=0,
        )
