from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend   
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiParameter, OpenApiTypes
from api.serializers.common import ErrorResponseSerializer
from products.models import Product
from api.serializers.product import ProductSerializer


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


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
        parameters=[
            OpenApiParameter(
               name="category",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter products by category id.",
            ),
            OpenApiParameter(
                name="include_unavailable",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="If true, include inactive or out-of-stock products.",
            ),
        ],
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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["name"]
    filterset_fields = {
        "category": ["exact"],
    }

    def get_queryset(self):
        qs = Product.objects.all()

        include_unavailable = _truthy(
            self.request.query_params.get("include_unavailable"))

        # TODO [SHOP-165]: Optional safety: only allow include_unavailable for authenticated users
        # if include_unavailable and self.request.user and self.request.user.is_authenticated:
        if include_unavailable:
            return qs.order_by("id")

        # Default FE-friendly behavior: only sellable
        return qs.filter(is_active=True, stock_quantity__gt=0).order_by("id")
