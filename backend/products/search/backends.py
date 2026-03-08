"""
Catalog search backends.

Each backend is responsible solely for text-search hit retrieval and relevance
scoring.  Business filtering (is_active, stock, price range, …) lives in the
service layer.

New backends (Elasticsearch, Typesense, …) implement CatalogSearchBackend and
are plugged in at the viewset level — the service and serializer are untouched.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import CatalogSearchQuery, SearchHit, SearchResult


@runtime_checkable
class CatalogSearchBackend(Protocol):
    """Minimal protocol every search backend must satisfy."""

    def search(self, query: CatalogSearchQuery) -> SearchResult:  # pragma: no cover
        ...


class MySQLCatalogSearchBackend:
    """
    MySQL FULLTEXT search backend.

    Executes MATCH … AGAINST in Boolean Mode over the three text columns that
    carry product content.  All MySQL-specific SQL is confined to this class —
    the service and viewset are completely database-agnostic.

    Prerequisites:
        A composite FULLTEXT index on (name, short_description, full_description)
        must exist (see migration 0004).
    """

    # Columns covered by the composite FULLTEXT index.  Order must match the
    # index definition.
    _COLUMNS = "name, short_description, full_description"

    def search(self, query: CatalogSearchQuery) -> SearchResult:
        if not query.search or not query.search.strip():
            return SearchResult()

        term = query.search.strip()

        sql = f"""
            SELECT id,
                   MATCH({self._COLUMNS}) AGAINST(%s IN BOOLEAN MODE) AS relevance
            FROM products_product
            WHERE MATCH({self._COLUMNS}) AGAINST(%s IN BOOLEAN MODE)
        """

        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(sql, [term, term])
            rows = cursor.fetchall()

        hits = [
            SearchHit(product_id=int(row[0]), relevance=float(row[1]))
            for row in rows
            if float(row[1]) > 0
        ]
        # Pre-sort by relevance descending so callers get a deterministic list.
        hits.sort(key=lambda h: h.relevance, reverse=True)
        return SearchResult(hits=hits)


class NullSearchBackend:
    """
    No-op backend used when no search engine is available (e.g. SQLite in
    development / CI unit tests).

    Any non-empty search term returns an empty result, which the service
    correctly translates to an empty catalogue response.
    """

    def search(self, query: CatalogSearchQuery) -> SearchResult:
        return SearchResult()
