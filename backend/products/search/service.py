"""
CatalogSearchService — pure Django ORM orchestration layer.

Responsibilities:
  * Enforce availability / staff-visibility rules.
  * Apply business filters (stock, category, price range).
  * Delegate text search to a CatalogSearchBackend.
  * Compose the final queryset with appropriate ordering.

This module contains NO database-vendor-specific SQL.  Relevance-based
ordering uses Django's Case/When, which is fully portable.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from django.db.models import Case, IntegerField, Max, Min, QuerySet, Value, When

from products.models import Product

from .backends import CatalogSearchBackend
from .types import CatalogSearchQuery

# ---------------------------------------------------------------------------
# Ordering maps for explicit sort params
# ---------------------------------------------------------------------------

_SORT_ORDERING: dict[str, list[str]] = {
    "price_asc": ["price", "name"],
    "price_desc": ["-price", "name"],
    "name_asc": ["name"],
    "name_desc": ["-name"],
}


class CatalogSearchService:
    """
    Builds a filtered and ordered Product queryset from a CatalogSearchQuery.

    Usage::

        backend = MySQLCatalogSearchBackend()   # or NullSearchBackend()
        service = CatalogSearchService(backend)
        qs = service.get_queryset(query, is_staff=request.user.is_staff)
    """

    def __init__(self, backend: CatalogSearchBackend) -> None:
        self.backend = backend

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_queryset(
        self,
        query: CatalogSearchQuery,
        *,
        is_staff: bool = False,
    ) -> QuerySet:
        qs = Product.objects.all()

        # --- Availability ----------------------------------------------------
        # include_unavailable is only honoured for staff/admin users.
        if query.include_unavailable and is_staff:
            pass  # show everything — inactive products included
        else:
            qs = qs.filter(is_active=True)

        # --- Stock filter ----------------------------------------------------
        if query.in_stock_only:
            qs = qs.filter(stock_quantity__gt=0)

        # --- Category --------------------------------------------------------
        if query.category_ids:
            qs = qs.filter(category_id__in=query.category_ids)

        # --- Price range -----------------------------------------------------
        if query.min_price is not None:
            qs = qs.filter(price__gte=query.min_price)
        if query.max_price is not None:
            qs = qs.filter(price__lte=query.max_price)

        # --- Text search -----------------------------------------------------
        if query.search and query.search.strip():
            result = self.backend.search(query)
            if result.is_empty:
                return qs.none()
            qs = qs.filter(pk__in=result.product_ids)
            return self._apply_ordering(qs, query, relevance_map=result.relevance_map)

        return self._apply_ordering(qs, query, relevance_map=None)

    def get_price_bounds(
        self,
        query: CatalogSearchQuery,
        *,
        is_staff: bool = False,
    ) -> tuple[Decimal | None, Decimal | None]:
        """
        Return (min_price, max_price) over the catalogue subset defined by
        *query*, but WITHOUT applying the price-range filter itself.

        Used to compute meaningful slider bounds for the FE price filter UI.
        """
        qs = Product.objects.all()

        if query.include_unavailable and is_staff:
            pass
        else:
            qs = qs.filter(is_active=True)

        if query.in_stock_only:
            qs = qs.filter(stock_quantity__gt=0)

        if query.category_ids:
            qs = qs.filter(category_id__in=query.category_ids)

        # Explicit text search: restrict to matched ids, same as main queryset.
        if query.search and query.search.strip():
            result = self.backend.search(query)
            if result.is_empty:
                return None, None
            qs = qs.filter(pk__in=result.product_ids)

        agg = qs.aggregate(lo=Min("price"), hi=Max("price"))
        return agg["lo"], agg["hi"]

    # ------------------------------------------------------------------
    # Internal ordering helpers
    # ------------------------------------------------------------------

    def _apply_ordering(
        self,
        qs: QuerySet,
        query: CatalogSearchQuery,
        *,
        relevance_map: Optional[dict[int, float]],
    ) -> QuerySet:
        # Explicit sort always wins.
        if query.sort in _SORT_ORDERING:
            return qs.order_by(*_SORT_ORDERING[query.sort])

        if relevance_map:
            # Relevance-based ordering:
            #   1. relevance DESC  (backend score, scaled to integer)
            #   2. availability    (in-stock first)
            #   3. name ASC
            #
            # Uses Case/When so ordering is expressed in pure Django ORM —
            # no vendor-specific SQL leaks into this layer.
            relevance_cases = [
                When(pk=pid, then=Value(int(rel * 1_000_000)))
                for pid, rel in relevance_map.items()
            ]
            qs = qs.annotate(
                _relevance=Case(
                    *relevance_cases,
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                _availability=self._availability_annotation(),
            )
            return qs.order_by("-_relevance", "_availability", "name")

        # Default catalogue ordering:
        #   1. in-stock first  (stock_quantity > 0)
        #   2. out-of-stock last
        #   3. name ASC within each group
        qs = qs.annotate(_availability=self._availability_annotation())
        return qs.order_by("_availability", "name")

    @staticmethod
    def _availability_annotation() -> Case:
        """0 for in-stock, 1 for out-of-stock — sorts ascending = in-stock first."""
        return Case(
            When(stock_quantity__gt=0, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
