from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiExample
from api.serializers.common import ErrorResponseSerializer
from categories.models import Category
from api.serializers.category import CategorySerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Categories"],
        summary="List product categories",
        description="""
Returns a flat list of categories.

Notes:
- Categories are read-only.
- No hierarchy is exposed (categories are flat).
""",
        responses={
            200: CategorySerializer,
        },
        examples=[
            OpenApiExample(
                name="Flat category list",
                value=[
                    {"id": 1, "name": "Electronics"},
                    {"id": 2, "name": "Accessories"},
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["Categories"],
        summary="Retrieve category detail",
        description="""
Returns details of a single category.

Notes:
- Categories are read-only.
- Categories are flat (no parent/children).
""",
        responses={
            200: CategorySerializer,
            404: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Category detail",
                value={"id": 1, "name": "Electronics"},
                response_only=True,
            ),
        ],
    ),
)
class CategoryViewSet(ReadOnlyModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.all()
