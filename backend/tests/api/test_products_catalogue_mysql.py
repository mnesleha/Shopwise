"""
MySQL catalogue search tests.

These tests require a real MySQL connection and are gated with @pytest.mark.mysql.
Run with:  pytest -m mysql tests/api/test_products_catalogue_mysql.py

They validate:
  - FULLTEXT search hits by name, short_description, full_description
  - Relevance-first ordering for search results
  - Availability as secondary ordering within equal-relevance hits
  - CatalogSearchService correctly composes backend hits with catalogue filters
"""

import pytest
from django.db import connection
from rest_framework.test import APIClient

from categories.models import Category
from products.models import Product
from products.search.backends import MySQLCatalogSearchBackend
from products.search.service import CatalogSearchService
from products.search.types import CatalogSearchQuery

URL = "/api/v1/products/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(**kwargs) -> Product:
    defaults = {"price": 10, "stock_quantity": 10, "is_active": True}
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


def _anon_client() -> APIClient:
    return APIClient()


# ---------------------------------------------------------------------------
# Search hits by field
# ---------------------------------------------------------------------------


@pytest.mark.mysql
@pytest.mark.django_db
def test_search_matches_name():
    """FULLTEXT search must surface a product matched by its name."""
    p = _make_product(name="WirelessKeyboard Pro", short_description="", full_description="")

    resp = _anon_client().get(URL, {"search": "WirelessKeyboard"})

    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert p.id in ids


@pytest.mark.mysql
@pytest.mark.django_db
def test_search_matches_short_description():
    """FULLTEXT search must surface a product matched by short_description."""
    p = _make_product(
        name="Generic Widget",
        short_description="Ergonomic mechanical keyboard with RGB backlight",
        full_description="",
    )
    # Unrelated product — must not appear.
    _make_product(name="Noise Product", short_description="completely unrelated")

    resp = _anon_client().get(URL, {"search": "Ergonomic"})

    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert p.id in ids
    assert Product.objects.get(name="Noise Product").id not in ids


@pytest.mark.mysql
@pytest.mark.django_db
def test_search_matches_full_description():
    """FULLTEXT search must surface a product matched in full_description."""
    p = _make_product(
        name="Plain Widget",
        short_description="",
        full_description="This product features quantum-dot display technology.",
    )
    _make_product(name="Other Product", short_description="", full_description="nothing relevant")

    resp = _anon_client().get(URL, {"search": "quantum-dot"})

    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert p.id in ids
    assert Product.objects.get(name="Other Product").id not in ids


# ---------------------------------------------------------------------------
# Search ordering: relevance-first
# ---------------------------------------------------------------------------


@pytest.mark.mysql
@pytest.mark.django_db
def test_search_ordering_relevance_first():
    """
    A product whose name is the search term should score higher than one that
    only mentions it in the full_description.
    """
    # High relevance: name == search term
    high = _make_product(
        name="Thunderbolt Dock",
        short_description="Thunderbolt Dock with 4K support",
        full_description="Thunderbolt Dock best-in-class connectivity",
    )
    # Low relevance: term appears only once, buried in full_description
    low = _make_product(
        name="Unrelated Hub",
        short_description="Basic USB hub",
        full_description="Great for everyday use. Thunderbolt not supported.",
    )

    resp = _anon_client().get(URL, {"search": "Thunderbolt"})

    assert resp.status_code == 200
    items = resp.json()
    ids = [item["id"] for item in items]
    assert high.id in ids
    assert low.id in ids
    assert ids.index(high.id) < ids.index(low.id), (
        "Higher-relevance product must appear before lower-relevance product"
    )


# ---------------------------------------------------------------------------
# Search ordering: availability as secondary sort
# ---------------------------------------------------------------------------


@pytest.mark.mysql
@pytest.mark.django_db
def test_search_ordering_availability_secondary():
    """
    When two products have similar relevance, in-stock must appear before
    out-of-stock.  We achieve this by creating two products with identical
    text content but different stock levels.
    """
    # Identical text content → same relevance score from MySQL.
    in_stock = _make_product(
        name="Bamboo Notebook",
        short_description="Eco bamboo notebook",
        full_description="",
        stock_quantity=10,
    )
    out_of_stock = _make_product(
        name="Bamboo Notebook",
        short_description="Eco bamboo notebook",
        full_description="",
        stock_quantity=0,
    )

    resp = _anon_client().get(URL, {"search": "Bamboo"})

    assert resp.status_code == 200
    items = resp.json()
    ids = [item["id"] for item in items]
    assert in_stock.id in ids
    assert out_of_stock.id in ids
    assert ids.index(in_stock.id) < ids.index(out_of_stock.id), (
        "In-stock product must precede out-of-stock when relevance is equal"
    )


# ---------------------------------------------------------------------------
# Service integration: search + catalogue filters
# ---------------------------------------------------------------------------


@pytest.mark.mysql
@pytest.mark.django_db
def test_service_search_with_category_filter():
    """Search results must be further filtered by category."""
    cat_a = Category.objects.create(name="Keyboards")
    cat_b = Category.objects.create(name="Mice")

    target = _make_product(
        name="MechKeyboard Alpha",
        short_description="Mechanical keyboard",
        category=cat_a,
    )
    _make_product(
        name="MechKeyboard Beta",
        short_description="Mechanical keyboard",
        category=cat_b,
    )

    resp = _anon_client().get(URL, {"search": "Mechanical", "category": cat_a.id})

    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    # Only the product in cat_a should appear.
    assert target.id in ids
    assert len(ids) == 1


@pytest.mark.mysql
@pytest.mark.django_db
def test_service_search_with_price_filter():
    """Search results must respect min_price / max_price."""
    cheap = _make_product(
        name="Budget Headset",
        short_description="Comfortable headset for gaming",
        price=15,
    )
    _make_product(
        name="Premium Headset",
        short_description="Comfortable headset for gaming",
        price=200,
    )

    resp = _anon_client().get(URL, {"search": "headset", "max_price": "50"})

    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert cheap.id in ids
    assert Product.objects.get(name="Premium Headset").id not in ids


@pytest.mark.mysql
@pytest.mark.django_db
def test_service_search_inactive_product_excluded_for_anon():
    """Inactive products must not appear in search results for anonymous users."""
    active = _make_product(
        name="Active Speaker",
        short_description="Wireless speaker",
        is_active=True,
    )
    _make_product(
        name="Inactive Speaker",
        short_description="Wireless speaker",
        is_active=False,
    )

    resp = _anon_client().get(URL, {"search": "speaker"})

    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert active.id in ids
    assert Product.objects.get(name="Inactive Speaker").id not in ids


@pytest.mark.mysql
@pytest.mark.django_db
def test_backend_returns_empty_for_blank_search():
    """MySQLCatalogSearchBackend must return empty SearchResult for blank term."""
    backend = MySQLCatalogSearchBackend()
    result = backend.search(CatalogSearchQuery(search=""))
    assert result.is_empty


@pytest.mark.mysql
@pytest.mark.django_db
def test_service_returns_empty_queryset_when_no_hits():
    """If backend returns no hits, service must return an empty queryset."""
    _make_product(name="Real Product", short_description="")

    backend = MySQLCatalogSearchBackend()
    service = CatalogSearchService(backend)
    query = CatalogSearchQuery(search="xyzzy_no_match_ever")

    qs = service.get_queryset(query)
    assert not qs.exists()
