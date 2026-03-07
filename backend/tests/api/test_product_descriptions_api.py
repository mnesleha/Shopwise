"""
API contract tests for Product description fields.

Covers:
- List endpoint includes short_description, omits full_description.
- Detail endpoint includes both short_description and full_description.
- Fields default to empty string when not explicitly set.
- Non-empty values are returned verbatim.
"""

import pytest
from rest_framework.test import APIClient
from products.models import Product


def _make_product(**kwargs) -> Product:
    defaults = dict(name="Test Product", price="9.99", stock_quantity=5, is_active=True)
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


# ── List endpoint ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_product_list_includes_short_description():
    """List response must contain short_description for every item."""
    _make_product(short_description="Quick teaser text")

    resp = APIClient().get("/api/v1/products/")

    assert resp.status_code == 200
    item = resp.json()[0]
    assert "short_description" in item
    assert item["short_description"] == "Quick teaser text"


@pytest.mark.django_db
def test_product_list_omits_full_description():
    """List response must NOT expose full_description (bandwidth optimisation)."""
    _make_product(full_description="# Long markdown content")

    resp = APIClient().get("/api/v1/products/")

    assert resp.status_code == 200
    item = resp.json()[0]
    assert "full_description" not in item


@pytest.mark.django_db
def test_product_list_short_description_defaults_to_empty_string():
    """short_description must default to '' when not set."""
    _make_product()

    resp = APIClient().get("/api/v1/products/")

    assert resp.status_code == 200
    assert resp.json()[0]["short_description"] == ""


# ── Detail endpoint ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_product_detail_includes_short_description():
    """Detail response must include short_description."""
    product = _make_product(short_description="Teaser for detail page")

    resp = APIClient().get(f"/api/v1/products/{product.id}/")

    assert resp.status_code == 200
    assert resp.json()["short_description"] == "Teaser for detail page"


@pytest.mark.django_db
def test_product_detail_includes_full_description():
    """Detail response must include full_description."""
    product = _make_product(full_description="## Heading\n\nSome **bold** text.")

    resp = APIClient().get(f"/api/v1/products/{product.id}/")

    assert resp.status_code == 200
    assert resp.json()["full_description"] == "## Heading\n\nSome **bold** text."


@pytest.mark.django_db
def test_product_detail_description_fields_default_to_empty_string():
    """Both description fields must default to '' when the product has none set."""
    product = _make_product()

    resp = APIClient().get(f"/api/v1/products/{product.id}/")

    assert resp.status_code == 200
    data = resp.json()
    assert data["short_description"] == ""
    assert data["full_description"] == ""
