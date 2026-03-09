"""
API tests for product image gallery — catalogue and detail endpoints.

Covers:
- Catalogue list serializer returns ``primary_image`` field only (no gallery).
- Detail serializer returns both ``primary_image`` and ``gallery_images``.
- ``primary_image`` is null when no primary image is set.
- Image payload contains ready-to-use URL variants: thumb, medium, large, full.
- Gallery ordering is deterministic (sort_order ASC, id ASC).
- Catalogue list does NOT expose ``gallery_images``.
"""

import pytest
from rest_framework.test import APIClient

from products.models import Product, ProductImage

LIST_URL = "/api/v1/products/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(**kwargs) -> Product:
    defaults = dict(name="Image Test Product", price="19.99", stock_quantity=5, is_active=True)
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


def _make_image(product: Product, sort_order: int = 0, alt_text: str = "") -> ProductImage:
    """Create a ProductImage without uploading an actual file."""
    return ProductImage.objects.create(
        product=product,
        image=f"products/gallery/img_{sort_order}_{product.pk}.jpg",
        alt_text=alt_text,
        sort_order=sort_order,
    )


def _set_primary(product: Product, img: ProductImage) -> None:
    """Directly assign primary_image bypassing Product.clean() (used for setup only)."""
    Product.objects.filter(pk=product.pk).update(primary_image=img)
    product.refresh_from_db()


# ---------------------------------------------------------------------------
# No image — primary_image is null
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_catalogue_primary_image_is_null_when_not_set():
    """Catalogue response must include primary_image=null for products with no image."""
    product = _make_product()

    resp = APIClient().get(LIST_URL)

    assert resp.status_code == 200
    items = resp.json()["results"]
    item = next(i for i in items if i["id"] == product.id)
    assert "primary_image" in item
    assert item["primary_image"] is None


@pytest.mark.django_db
def test_detail_primary_image_is_null_when_not_set():
    """Detail response must include primary_image=null for products with no image."""
    product = _make_product()

    resp = APIClient().get(f"{LIST_URL}{product.id}/")

    assert resp.status_code == 200
    data = resp.json()
    assert "primary_image" in data
    assert data["primary_image"] is None


# ---------------------------------------------------------------------------
# Catalogue serializer — only primary_image, no gallery
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_catalogue_returns_primary_image_not_gallery():
    """Catalogue list must expose primary_image but must NOT expose gallery_images."""
    product = _make_product()
    img = _make_image(product)
    _set_primary(product, img)

    resp = APIClient().get(LIST_URL)

    assert resp.status_code == 200
    items = resp.json()["results"]
    item = next(i for i in items if i["id"] == product.id)

    assert "primary_image" in item
    assert "gallery_images" not in item


@pytest.mark.django_db
def test_catalogue_primary_image_contains_url_variants():
    """Catalogue primary_image payload must include thumb, medium, large, full keys."""
    product = _make_product()
    img = _make_image(product, alt_text="Hero shot")
    _set_primary(product, img)

    resp = APIClient().get(LIST_URL)

    assert resp.status_code == 200
    items = resp.json()["results"]
    item = next(i for i in items if i["id"] == product.id)

    pi = item["primary_image"]
    assert pi is not None
    assert "image" in pi
    image_payload = pi["image"]
    for variant in ("thumb", "medium", "large", "full"):
        assert variant in image_payload, f"Missing variant: {variant}"
        assert isinstance(image_payload[variant], str), f"Variant {variant!r} must be a string URL"
        assert image_payload[variant], f"Variant {variant!r} must not be empty"


# ---------------------------------------------------------------------------
# Detail serializer — primary_image + gallery_images
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_detail_returns_primary_image_and_gallery_images():
    """Detail endpoint must return both primary_image and gallery_images."""
    product = _make_product()
    img = _make_image(product)
    _set_primary(product, img)

    resp = APIClient().get(f"{LIST_URL}{product.id}/")

    assert resp.status_code == 200
    data = resp.json()
    assert "primary_image" in data
    assert "gallery_images" in data


@pytest.mark.django_db
def test_detail_gallery_images_contains_all_images():
    """gallery_images must list all ProductImages belonging to the product."""
    product = _make_product()
    img1 = _make_image(product, sort_order=0)
    img2 = _make_image(product, sort_order=1)
    img3 = _make_image(product, sort_order=2)

    resp = APIClient().get(f"{LIST_URL}{product.id}/")

    assert resp.status_code == 200
    gallery = resp.json()["gallery_images"]
    assert len(gallery) == 3
    returned_ids = {g["id"] for g in gallery}
    assert returned_ids == {img1.pk, img2.pk, img3.pk}


@pytest.mark.django_db
def test_detail_gallery_images_contains_url_variants():
    """Each gallery image payload must include thumb, medium, large, full variants."""
    product = _make_product()
    _make_image(product, sort_order=0, alt_text="Gallery image")

    resp = APIClient().get(f"{LIST_URL}{product.id}/")

    assert resp.status_code == 200
    gallery = resp.json()["gallery_images"]
    assert len(gallery) == 1

    image_payload = gallery[0]["image"]
    for variant in ("thumb", "medium", "large", "full"):
        assert variant in image_payload, f"Missing variant: {variant}"
        assert isinstance(image_payload[variant], str), f"Variant {variant!r} must be a string URL"
        assert image_payload[variant], f"Variant {variant!r} must not be empty"


@pytest.mark.django_db
def test_detail_gallery_images_empty_when_no_images():
    """gallery_images must be an empty list when no ProductImages exist."""
    product = _make_product()

    resp = APIClient().get(f"{LIST_URL}{product.id}/")

    assert resp.status_code == 200
    assert resp.json()["gallery_images"] == []


# ---------------------------------------------------------------------------
# Gallery ordering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_gallery_ordering_by_sort_order():
    """gallery_images must be ordered by sort_order ascending."""
    product = _make_product()
    img_c = _make_image(product, sort_order=10)
    img_a = _make_image(product, sort_order=1)
    img_b = _make_image(product, sort_order=5)

    resp = APIClient().get(f"{LIST_URL}{product.id}/")

    assert resp.status_code == 200
    gallery = resp.json()["gallery_images"]
    returned_ids = [g["id"] for g in gallery]
    assert returned_ids == [img_a.pk, img_b.pk, img_c.pk]


@pytest.mark.django_db
def test_gallery_ordering_by_id_when_sort_order_equal():
    """When sort_order is equal, gallery must be ordered by id ascending."""
    product = _make_product()
    img1 = _make_image(product, sort_order=0)
    img2 = _make_image(product, sort_order=0)
    img3 = _make_image(product, sort_order=0)

    resp = APIClient().get(f"{LIST_URL}{product.id}/")

    assert resp.status_code == 200
    gallery = resp.json()["gallery_images"]
    returned_ids = [g["id"] for g in gallery]
    assert returned_ids == sorted([img1.pk, img2.pk, img3.pk])
