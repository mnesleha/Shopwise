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
Returns the category tree used for product classification.

Behavior:
- Only parent (root) categories are returned.
- Child categories are nested under their parent.
- Category hierarchy is limited to two levels (parent → children).

Notes:
- Categories are read-only.
- Leaf categories are not exposed as top-level resources.
""",
        responses={
            200: CategorySerializer,
        },
        examples=[
            OpenApiExample(
                name="Category tree",
                value=[
                    {
                        "id": 1,
                        "name": "Electronics",
                        "is_parent": True,
                        "children": [
                            {
                                "id": 2,
                                "name": "Accessories",
                                "is_parent": False,
                                "children": []
                            }
                        ]
                    }
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
- Both parent and leaf categories can be retrieved by ID.
""",
        responses={
            200: CategorySerializer,
            404: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Category detail",
                value={
                    "id": 1,
                    "name": "Electronics",
                    "is_parent": True,
                    "children": [
                        {
                            "id": 2,
                            "name": "Accessories",
                            "is_parent": False,
                            "children": []
                        }
                    ]
                },
                response_only=True,
            ),
        ],
    ),
)
class CategoryViewSet(ReadOnlyModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(
            is_parent=True
        ).prefetch_related("children")
