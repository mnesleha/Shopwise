"""
Shared data types for the catalog search layer.

These types are intentionally plain dataclasses — no Django ORM, no HTTP, no
business logic.  Any backend or service may import them safely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class CatalogSearchQuery:
    """All inputs that drive a single catalog listing / search request."""

    search: Optional[str] = None
    # Multi-select category filter.  Empty list means "all categories".
    category_ids: list = field(default_factory=list)
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    in_stock_only: bool = False
    # Honoured only for staff users — service enforces the constraint.
    include_unavailable: bool = False
    # Explicit sort key.  None means "use default availability-first ordering".
    sort: Optional[str] = None  # price_asc | price_desc | name_asc | name_desc


@dataclass
class SearchHit:
    """A single product matched by a text search backend, with its relevance score."""

    product_id: int
    relevance: float = 1.0


@dataclass
class SearchResult:
    """All hits returned by a CatalogSearchBackend for one query."""

    hits: list[SearchHit] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.hits) == 0

    @property
    def product_ids(self) -> list[int]:
        return [h.product_id for h in self.hits]

    @property
    def relevance_map(self) -> dict[int, float]:
        """Map of product_id → relevance score, for ordering annotation."""
        return {h.product_id: h.relevance for h in self.hits}
