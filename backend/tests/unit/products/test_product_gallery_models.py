"""
Unit tests for ProductImage model and related Product.primary_image behaviour.

Covers:
- ProductImage can be created and persists correctly.
- primary_image must belong to the same product (ValidationError otherwise).
- Deleting a ProductImage that is the primary_image nulls Product.primary_image
  (on_delete=SET_NULL).
- PPOI field wiring: VersatileImageField has ppoi_field set; admin formfield
  returns the click-widget field class.
"""

import pytest
from django.contrib.admin.widgets import AdminFileWidget
from django.core.exceptions import ValidationError
from versatileimagefield.forms import SizedImageCenterpointClickDjangoAdminField

from products.models import Product, ProductImage, _product_gallery_upload_to

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(**kwargs) -> Product:
    defaults = dict(name="Gallery Test Product", price="9.99", stock_quantity=10, is_active=True)
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


def _make_image(product: Product, sort_order: int = 0) -> ProductImage:
    """Create a ProductImage with a fake path (no file required for constraint tests)."""
    return ProductImage.objects.create(
        product=product,
        image=f"products/gallery/test_{sort_order}.png",
        alt_text="",
        sort_order=sort_order,
    )


# ---------------------------------------------------------------------------
# Basic creation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_product_image_can_be_created():
    """A ProductImage can be persisted and retrieved."""
    product = _make_product()
    img = _make_image(product, sort_order=1)

    assert img.pk is not None
    assert img.product_id == product.pk
    assert img.sort_order == 1
    assert img.created_at is not None


# ---------------------------------------------------------------------------
# primary_image ownership
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_primary_image_must_belong_to_same_product():
    """Setting primary_image to an image of a different product raises ValidationError."""
    p1 = _make_product(name="Product 1")
    p2 = _make_product(name="Product 2")

    img_for_p2 = _make_image(p2)

    p1.primary_image = img_for_p2

    with pytest.raises(ValidationError) as exc_info:
        p1.full_clean()

    errors = exc_info.value.message_dict
    assert "primary_image" in errors


@pytest.mark.django_db
def test_primary_image_from_same_product_passes_validation():
    """Setting primary_image to an image of the same product passes clean()."""
    product = _make_product()
    img = _make_image(product)

    product.primary_image = img
    # Must not raise.
    product.full_clean()


# ---------------------------------------------------------------------------
# Deleting primary image nulls Product.primary_image
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_deleting_primary_image_nulls_product_primary_image():
    """When the designated primary image is deleted, Product.primary_image is set to null."""
    product = _make_product()
    img = _make_image(product)

    # Assign as primary, save explicitly (bypassing full_clean for simplicity).
    Product.objects.filter(pk=product.pk).update(primary_image=img)
    product.refresh_from_db()
    assert product.primary_image_id == img.pk

    img.delete()

    product.refresh_from_db()
    assert product.primary_image_id is None


@pytest.mark.django_db
def test_deleting_non_primary_image_does_not_affect_primary_image():
    """Deleting a non-primary gallery image leaves Product.primary_image unchanged."""
    product = _make_product()
    primary = _make_image(product, sort_order=0)
    other = _make_image(product, sort_order=1)

    Product.objects.filter(pk=product.pk).update(primary_image=primary)
    product.refresh_from_db()

    other.delete()

    product.refresh_from_db()
    assert product.primary_image_id == primary.pk


# ---------------------------------------------------------------------------
# Upload path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upload_path_contains_product_id():
    """Saved upload path must be ``products/gallery/<product_id>/<filename>``."""
    product = _make_product()
    # Build a minimal unsaved instance with the FK already set.
    instance = ProductImage(product=product)

    path = _product_gallery_upload_to(instance, "photo.jpg")

    assert path == f"products/gallery/{product.pk}/photo.jpg"


def test_upload_path_fallback_when_no_product_id():
    """When product_id is unknown the path falls back to ``products/gallery/unsorted/``."""
    instance = ProductImage()  # product not assigned yet

    path = _product_gallery_upload_to(instance, "photo.jpg")

    assert path == "products/gallery/unsorted/photo.jpg"


# ---------------------------------------------------------------------------
# PPOI field wiring
# ---------------------------------------------------------------------------


def test_image_field_has_ppoi_field_set():
    """ProductImage.image must declare ppoi_field='ppoi'.

    This is the prerequisite for the admin PPOI click-widget: without it
    VersatileImageField.formfield() falls back to a plain file input and the
    focal-point picker is never rendered.
    """
    image_field = ProductImage._meta.get_field("image")
    assert image_field.ppoi_field == "ppoi", (
        "VersatileImageField must have ppoi_field='ppoi' so the admin renders "
        "SizedImageCenterpointClickDjangoAdminField instead of a plain file input."
    )


def test_image_formfield_in_admin_uses_ppoi_click_widget():
    """Admin formfield for ProductImage.image must be SizedImageCenterpointClickDjangoAdminField.

    Django admin passes ``widget=AdminFileWidget`` to formfield(); VersatileImageField
    detects that, drops it, and (because ppoi_field is set) returns the PPOI click
    field instead.  This is the field that renders the clickable focal-point preview.
    """
    image_field = ProductImage._meta.get_field("image")
    # Simulate how Django admin calls formfield() — it passes the AdminFileWidget.
    form_field = image_field.formfield(widget=AdminFileWidget)
    assert isinstance(form_field, SizedImageCenterpointClickDjangoAdminField), (
        f"Expected SizedImageCenterpointClickDjangoAdminField, got {type(form_field).__name__}. "
        "Check that ppoi_field='ppoi' is present on the VersatileImageField."
    )
