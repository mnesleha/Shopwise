"""
Products viewset — catalogue listing and detail retrieval.

This is intentionally thin: query-param parsing, backend selection and
queryset construction are delegated to CatalogSearchService.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.serializers.common import ErrorResponseSerializer
from api.serializers.product import ProductDetailSerializer, ProductSerializer
from products.search.backends import MySQLCatalogSearchBackend, NullSearchBackend
from products.search.service import CatalogSearchService
from products.search.types import CatalogSearchQuery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        return None


def _build_backend():
    """Return the appropriate search backend for the current database engine."""
    from django.db import connection

    if connection.vendor == "mysql":
        return MySQLCatalogSearchBackend()
    return NullSearchBackend()


def _parse_category_ids(params) -> list[int]:
    """Parse repeated ?category=<id>&category=<id> query params into a list of ints."""
    raw = params.getlist("category")
    ids = []
    for v in raw:
        try:
            ids.append(int(v))
        except (ValueError, TypeError):
            pass
    return ids


# ---------------------------------------------------------------------------
# OpenAPI decorators
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(
        tags=["Products"],
        summary="List products (catalogue)",
        description="""
Returns the product catalogue with optional filtering and full-text search.

Response shape:
```json
{
  "results": [ ...products... ],
  "metadata": {
    "price_min_available": "5.00",
    "price_max_available": "999.99"
  }
}
```

**Default behaviour** (no query params):
- Only `is_active=True` products are returned.
- Out-of-stock products are included but sorted last (in-stock first, then name ASC).

**Query params:**
- `search` — Full-text search across name, short_description, full_description.
  On MySQL results are ordered by relevance first.
- `category` — Filter by category id (repeatable: `?category=1&category=2` → OR).
- `min_price` / `max_price` — Numeric price range (inclusive).
- `in_stock_only=true` — Restrict to products with `stock_quantity > 0`.
- `include_unavailable=true` — Staff/admin only: include `is_active=False` products.
- `sort` — Explicit sort: `price_asc | price_desc | name_asc | name_desc`.
""",
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Full-text search across product name and descriptions.",
            ),
            OpenApiParameter(
                name="category",
                type={"type": "array", "items": {"type": "integer"}},
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filter by category id. Repeatable for multi-select OR behaviour: "
                    "?category=1&category=2"
                ),
                style="form",
                explode=True,
            ),
            OpenApiParameter(
                name="min_price",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Minimum price (inclusive).",
            ),
            OpenApiParameter(
                name="max_price",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Maximum price (inclusive).",
            ),
            OpenApiParameter(
                name="in_stock_only",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="If true, return only products with stock_quantity > 0.",
            ),
            OpenApiParameter(
                name="include_unavailable",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Staff/admin only: if true, include inactive (is_active=False) "
                    "products. Ignored for non-staff users."
                ),
            ),
            OpenApiParameter(
                name="sort",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Sort order. One of: price_asc, price_desc, name_asc, name_desc. "
                    "Omit to use default availability-first ordering."
                ),
                enum=["price_asc", "price_desc", "name_asc", "name_desc"],
            ),
        ],
        responses={200: None},  # custom shape — described in description
        examples=[
            OpenApiExample(
                name="Catalogue list",
                value={
                    "results": [
                        {
                            "id": 1,
                            "name": "Wireless Mouse",
                            "category_id": 3,
                            "price": "29.99",
                            "stock_quantity": 15,
                            "stock_status": "IN_STOCK",
                            "short_description": "Compact wireless mouse.",
                        }
                    ],
                    "metadata": {
                        "price_min_available": "5.00",
                        "price_max_available": "299.99",
                    },
                },
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["Products"],
        summary="Retrieve product detail",
        description="Returns details of a single active product.",
        responses={
            200: ProductDetailSerializer,
            404: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Product detail",
                value={
                    "id": 1,
                    "name": "Wireless Mouse",
                    "category_id": 3,
                    "price": "29.99",
                    "stock_quantity": 15,
                    "stock_status": "IN_STOCK",
                    "short_description": "Compact wireless mouse for everyday use.",
                    "full_description": "## Wireless Mouse\n\nA reliable companion.",
                },
                response_only=True,
            ),
        ],
    ),
)
class ProductViewSet(ReadOnlyModelViewSet):
    serializer_class = ProductSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductSerializer

    def _build_query(self) -> CatalogSearchQuery:
        params = self.request.query_params
        return CatalogSearchQuery(
            search=params.get("search") or None,
            category_ids=_parse_category_ids(params),
            min_price=_decimal_or_none(params.get("min_price")),
            max_price=_decimal_or_none(params.get("max_price")),
            in_stock_only=_truthy(params.get("in_stock_only")),
            include_unavailable=_truthy(params.get("include_unavailable")),
            sort=params.get("sort") or None,
        )

    def _is_staff(self) -> bool:
        return bool(
            self.request.user
            and self.request.user.is_authenticated
            and self.request.user.is_staff
        )

    def get_queryset(self):
        service = CatalogSearchService(_build_backend())
        return service.get_queryset(self._build_query(), is_staff=self._is_staff())

    def list(self, request, *args, **kwargs):
        """
        Override list to include price-range metadata alongside the results.

        Response shape::

            {
                "results": [...products...],
                "metadata": {
                    "price_min_available": "X.XX",
                    "price_max_available": "Y.YY"
                }
            }

        ``price_min_available`` / ``price_max_available`` reflect the full
        price range of the current filtered subset (ignoring min_price /
        max_price params), so the FE can initialise slider bounds from them.
        """
        qs = self.get_queryset()

        # Serialise the results list.
        serializer = self.get_serializer(qs, many=True)

        # Price bounds — computed without applying the price filter.
        service = CatalogSearchService(_build_backend())
        lo, hi = service.get_price_bounds(self._build_query(), is_staff=self._is_staff())

        metadata = {
            "price_min_available": str(lo) if lo is not None else None,
            "price_max_available": str(hi) if hi is not None else None,
        }

        return Response({"results": serializer.data, "metadata": metadata})
