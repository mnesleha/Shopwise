"""
Catalogue API tests â€” SQLite / generic (no MySQL-specific behaviour).

These tests cover:
  - Default list behaviour (active-only, out-of-stock sorted last)
  - All query param filters: category (single + multi), min_price, max_price,
    in_stock_only
  - include_unavailable: honoured for staff, ignored for non-staff
  - sort params: price_asc, price_desc, name_asc, name_desc
  - stock_status field in serializer responses
  - Price metadata in response
  - Blank / absent search falls back to standard catalogue behaviour
  - Search with no hits returns empty valid response (NullSearchBackend)
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from categories.models import Category
from products.models import Product

URL = "/api/v1/products/"

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(**kwargs) -> Product:
    defaults = {"price": 10, "stock_quantity": 10, "is_active": True}
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


def _staff_client(db) -> APIClient:
    staff = User.objects.create_user(
        email="staff@example.com",
        password="Passw0rd!123",
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=staff)
    return client


def _anon_client() -> APIClient:
    return APIClient()


def _data(resp) -> list:
    """Unwrap ``results`` from the catalogue response envelope."""
    return resp.json()["results"]


def _metadata(resp) -> dict:
    """Unwrap ``metadata`` from the catalogue response envelope."""
    return resp.json()["metadata"]


# ---------------------------------------------------------------------------
# Default list behaviour
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_default_list_returns_only_active_products():
    """Inactive products must never appear in the default catalogue response."""
    active = _make_product(name="Active", is_active=True)
    _make_product(name="Inactive", is_active=False)

    resp = _anon_client().get(URL)

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert active.id in ids
    assert Product.objects.get(name="Inactive").id not in ids


@pytest.mark.django_db
def test_default_list_includes_out_of_stock_products():
    """Out-of-stock products are included by default (not filtered out)."""
    in_stock = _make_product(name="In Stock", stock_quantity=5)
    out_of_stock = _make_product(name="Out Of Stock", stock_quantity=0)

    resp = _anon_client().get(URL)

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert in_stock.id in ids
    assert out_of_stock.id in ids


@pytest.mark.django_db
def test_default_list_orders_out_of_stock_last():
    """
    Default ordering: in-stock first, out-of-stock last, name ASC within each group.
    """
    _make_product(name="Beta", stock_quantity=0)   # out-of-stock
    _make_product(name="Alpha", stock_quantity=5)  # in-stock
    _make_product(name="Gamma", stock_quantity=0)  # out-of-stock
    _make_product(name="Delta", stock_quantity=3)  # in-stock

    resp = _anon_client().get(URL)

    assert resp.status_code == 200
    names = [item["name"] for item in _data(resp)]

    in_stock_names = ["Alpha", "Delta"]
    out_of_stock_names = ["Beta", "Gamma"]

    in_stock_indices = [names.index(n) for n in in_stock_names]
    out_of_stock_indices = [names.index(n) for n in out_of_stock_names]

    assert max(in_stock_indices) < min(out_of_stock_indices), (
        f"Expected all in-stock before all out-of-stock. Got: {names}"
    )

    assert names.index("Alpha") < names.index("Delta")
    assert names.index("Beta") < names.index("Gamma")


# ---------------------------------------------------------------------------
# Filter: category (single + multi)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_filter_by_single_category():
    cat1 = Category.objects.create(name="Electronics")
    cat2 = Category.objects.create(name="Clothing")

    p1 = _make_product(name="Mouse", category=cat1)
    _make_product(name="T-Shirt", category=cat2)

    resp = _anon_client().get(URL, {"category": cat1.id})

    assert resp.status_code == 200
    data = _data(resp)
    assert len(data) == 1
    assert data[0]["id"] == p1.id


@pytest.mark.django_db
def test_filter_by_multiple_categories_returns_union():
    """Multi-select categories use OR semantics."""
    cat1 = Category.objects.create(name="Electronics")
    cat2 = Category.objects.create(name="Clothing")
    cat3 = Category.objects.create(name="Food")

    p1 = _make_product(name="Mouse", category=cat1)
    p2 = _make_product(name="T-Shirt", category=cat2)
    p3 = _make_product(name="Apple", category=cat3)

    resp = _anon_client().get(f"{URL}?category={cat1.id}&category={cat2.id}")

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert p1.id in ids
    assert p2.id in ids
    assert p3.id not in ids


@pytest.mark.django_db
def test_filter_by_multiple_categories_with_price_filter():
    """Multi-category filter composes correctly with price filter."""
    cat1 = Category.objects.create(name="Electronics")
    cat2 = Category.objects.create(name="Clothing")

    _make_product(name="Expensive Mouse", price=500, category=cat1)
    cheap_shirt = _make_product(name="Cheap Shirt", price=10, category=cat2)
    _make_product(name="Cheap Mouse", price=10, category=cat1)

    resp = _anon_client().get(
        f"{URL}?category={cat1.id}&category={cat2.id}&max_price=20"
    )

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert cheap_shirt.id in ids
    assert Product.objects.get(name="Cheap Mouse").id in ids
    assert Product.objects.get(name="Expensive Mouse").id not in ids


@pytest.mark.django_db
def test_filter_by_category_legacy_compat():
    """Single ?category=<id> still works (backward compat)."""
    cat = Category.objects.create(name="Electronics")
    product = _make_product(name="Keyboard", category=cat)
    _make_product(name="Other", price=5)

    resp = _anon_client().get(URL, {"category": cat.id})

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert product.id in ids
    assert len(ids) == 1


# ---------------------------------------------------------------------------
# Filter: price range
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_filter_min_price():
    _make_product(name="Cheap", price=5)
    expensive = _make_product(name="Expensive", price=100)

    resp = _anon_client().get(URL, {"min_price": "50"})

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert expensive.id in ids
    assert Product.objects.get(name="Cheap").id not in ids


@pytest.mark.django_db
def test_filter_max_price():
    cheap = _make_product(name="Cheap", price=5)
    _make_product(name="Expensive", price=100)

    resp = _anon_client().get(URL, {"max_price": "20"})

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert cheap.id in ids
    assert Product.objects.get(name="Expensive").id not in ids


@pytest.mark.django_db
def test_filter_price_range():
    _make_product(name="Too Cheap", price=5)
    mid = _make_product(name="Just Right", price=50)
    _make_product(name="Too Expensive", price=200)

    resp = _anon_client().get(URL, {"min_price": "10", "max_price": "100"})

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert mid.id in ids
    assert len(ids) == 1


# ---------------------------------------------------------------------------
# Filter: in_stock_only
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_in_stock_only_filters_out_of_stock():
    in_stock = _make_product(name="In Stock", stock_quantity=10)
    _make_product(name="Out of Stock", stock_quantity=0)

    resp = _anon_client().get(URL, {"in_stock_only": "true"})

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert in_stock.id in ids
    assert Product.objects.get(name="Out of Stock").id not in ids


@pytest.mark.django_db
def test_in_stock_only_false_includes_out_of_stock():
    _make_product(name="In Stock", stock_quantity=5)
    out = _make_product(name="Out of Stock", stock_quantity=0)

    resp = _anon_client().get(URL, {"in_stock_only": "false"})

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert out.id in ids


# ---------------------------------------------------------------------------
# Filter: include_unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_include_unavailable_ignored_for_non_staff():
    """Non-staff users must never see inactive products regardless of the param."""
    _make_product(name="Active", is_active=True)
    inactive = _make_product(name="Inactive", is_active=False)

    resp = _anon_client().get(URL, {"include_unavailable": "true"})

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert inactive.id not in ids


@pytest.mark.django_db
def test_include_unavailable_honoured_for_staff(db):
    """Staff users with include_unavailable=true receive inactive products too."""
    active = _make_product(name="Active", is_active=True)
    inactive = _make_product(name="Inactive", is_active=False)

    client = _staff_client(db)
    resp = client.get(URL, {"include_unavailable": "true"})

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert active.id in ids
    assert inactive.id in ids


@pytest.mark.django_db
def test_include_unavailable_false_still_hides_inactive_for_staff(db):
    """Staff without include_unavailable=true should also not see inactive."""
    _make_product(name="Active", is_active=True)
    inactive = _make_product(name="Inactive", is_active=False)

    client = _staff_client(db)
    resp = client.get(URL)  # no include_unavailable param

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert inactive.id not in ids


# ---------------------------------------------------------------------------
# Sort params
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sort_price_asc():
    _make_product(name="Expensive", price=100)
    _make_product(name="Cheap", price=10)
    _make_product(name="Mid", price=50)

    resp = _anon_client().get(URL, {"sort": "price_asc"})

    assert resp.status_code == 200
    prices = [Decimal(item["price"]) for item in _data(resp)]
    assert prices == sorted(prices)


@pytest.mark.django_db
def test_sort_price_desc():
    _make_product(name="Expensive", price=100)
    _make_product(name="Cheap", price=10)
    _make_product(name="Mid", price=50)

    resp = _anon_client().get(URL, {"sort": "price_desc"})

    assert resp.status_code == 200
    prices = [Decimal(item["price"]) for item in _data(resp)]
    assert prices == sorted(prices, reverse=True)


@pytest.mark.django_db
def test_sort_name_asc():
    for name in ["Zeta", "Alpha", "Mu"]:
        _make_product(name=name)

    resp = _anon_client().get(URL, {"sort": "name_asc"})

    assert resp.status_code == 200
    names = [item["name"] for item in _data(resp)]
    assert names == sorted(names)


@pytest.mark.django_db
def test_sort_name_desc():
    for name in ["Zeta", "Alpha", "Mu"]:
        _make_product(name=name)

    resp = _anon_client().get(URL, {"sort": "name_desc"})

    assert resp.status_code == 200
    names = [item["name"] for item in _data(resp)]
    assert names == sorted(names, reverse=True)


# ---------------------------------------------------------------------------
# Serializer: stock_status
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_serializer_stock_status_in_stock(settings):
    settings.LOW_STOCK_THRESHOLD = 5
    _make_product(name="Rich Stock", stock_quantity=100)

    resp = _anon_client().get(URL)

    assert resp.status_code == 200
    item = next(i for i in _data(resp) if i["name"] == "Rich Stock")
    assert item["stock_status"] == "IN_STOCK"


@pytest.mark.django_db
def test_serializer_stock_status_low_stock(settings):
    settings.LOW_STOCK_THRESHOLD = 5
    _make_product(name="Low Stock", stock_quantity=3)

    resp = _anon_client().get(URL)

    assert resp.status_code == 200
    item = next(i for i in _data(resp) if i["name"] == "Low Stock")
    assert item["stock_status"] == "LOW_STOCK"


@pytest.mark.django_db
def test_serializer_stock_status_out_of_stock():
    _make_product(name="No Stock", stock_quantity=0)

    resp = _anon_client().get(URL)

    assert resp.status_code == 200
    item = next(i for i in _data(resp) if i["name"] == "No Stock")
    assert item["stock_status"] == "OUT_OF_STOCK"


@pytest.mark.django_db
def test_detail_serializer_includes_stock_status():
    p = _make_product(name="Detail Product", stock_quantity=10)

    resp = _anon_client().get(f"{URL}{p.id}/")

    assert resp.status_code == 200
    data = resp.json()
    assert "stock_status" in data
    assert data["stock_status"] == "IN_STOCK"


# ---------------------------------------------------------------------------
# Price metadata
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_response_includes_price_metadata():
    """List response must include metadata.price_min_available and price_max_available."""
    _make_product(name="Cheap", price=5)
    _make_product(name="Mid", price=50)
    _make_product(name="Expensive", price=200)

    resp = _anon_client().get(URL)

    assert resp.status_code == 200
    meta = _metadata(resp)
    assert "price_min_available" in meta
    assert "price_max_available" in meta
    assert Decimal(meta["price_min_available"]) == Decimal("5")
    assert Decimal(meta["price_max_available"]) == Decimal("200")


@pytest.mark.django_db
def test_price_metadata_reflects_full_range_ignoring_price_filter():
    """
    Price metadata must reflect the full range of the subset WITHOUT applying
    the price filter parameters â€” so the FE slider always shows the full range.
    """
    _make_product(name="Cheap", price=5)
    _make_product(name="Expensive", price=200)

    # Apply price filter â€” only the "Cheap" product is in results.
    resp = _anon_client().get(URL, {"max_price": "10"})

    assert resp.status_code == 200
    meta = _metadata(resp)
    # Despite the filter cutting results to only the cheap product,
    # metadata must still show the full available range.
    assert Decimal(meta["price_min_available"]) == Decimal("5")
    assert Decimal(meta["price_max_available"]) == Decimal("200")


@pytest.mark.django_db
def test_price_metadata_is_null_when_no_products():
    """When the catalogue is empty, price bounds should be null."""
    resp = _anon_client().get(URL)

    assert resp.status_code == 200
    meta = _metadata(resp)
    assert meta["price_min_available"] is None
    assert meta["price_max_available"] is None


@pytest.mark.django_db
def test_price_metadata_respects_category_filter():
    """Price bounds are scoped to the selected categories."""
    cat1 = Category.objects.create(name="Electronics")
    cat2 = Category.objects.create(name="Clothing")

    _make_product(name="Expensive Electronics", price=500, category=cat1)
    _make_product(name="Cheap Clothing", price=10, category=cat2)

    resp = _anon_client().get(URL, {"category": cat2.id})

    assert resp.status_code == 200
    meta = _metadata(resp)
    assert Decimal(meta["price_min_available"]) == Decimal("10")
    assert Decimal(meta["price_max_available"]) == Decimal("10")


# ---------------------------------------------------------------------------
# Search fallback behaviour (NullSearchBackend on SQLite)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_search_param_returns_standard_catalogue():
    """Omitting search entirely must return normal catalogue with active products."""
    p = _make_product(name="Visible Product")

    resp = _anon_client().get(URL)

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert p.id in ids


@pytest.mark.django_db
def test_blank_search_returns_standard_catalogue():
    """search= (empty string) must fall back to standard catalogue behaviour."""
    p = _make_product(name="Should Appear")

    resp = _anon_client().get(URL, {"search": ""})

    assert resp.status_code == 200
    ids = {item["id"] for item in _data(resp)}
    assert p.id in ids


@pytest.mark.django_db
def test_search_no_hits_returns_empty_valid_response():
    """
    On SQLite (NullSearchBackend) any non-empty search returns empty results.
    The response must be HTTP 200 with results=[].
    """
    _make_product(name="Some Product")

    resp = _anon_client().get(URL, {"search": "nonexistent"})

    assert resp.status_code == 200
    assert _data(resp) == []


