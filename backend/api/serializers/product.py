from django.conf import settings
from rest_framework import serializers
from versatileimagefield.serializers import VersatileImageFieldSerializer

from products.models import Product, ProductImage

# ---------------------------------------------------------------------------
# Stock status constants
# ---------------------------------------------------------------------------

IN_STOCK = "IN_STOCK"
LOW_STOCK = "LOW_STOCK"
OUT_OF_STOCK = "OUT_OF_STOCK"

_STOCK_STATUS_CHOICES = [IN_STOCK, LOW_STOCK, OUT_OF_STOCK]

# VersatileImageField size keys used for all image payloads.
# FE consumers must use these URLs directly — never construct media paths.
_IMAGE_SIZES = [
    ("thumb", "thumbnail__100x100"),
    ("medium", "thumbnail__400x400"),
    ("large", "thumbnail__800x800"),
    ("full", "url"),
]


def _compute_stock_status(stock_quantity: int) -> str:
    threshold: int = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
    if stock_quantity <= 0:
        return OUT_OF_STOCK
    if stock_quantity <= threshold:
        return LOW_STOCK
    return IN_STOCK


# ---------------------------------------------------------------------------
# Image serializers
# ---------------------------------------------------------------------------


class ProductImageSerializer(serializers.ModelSerializer):
    """Serialises a ProductImage with ready-to-use URL variants.

    All URL variants are absolute when a ``request`` is present in context.
    FE must not construct media URLs — consume ``thumb``, ``medium``,
    ``large``, or ``full`` directly.
    """

    image = VersatileImageFieldSerializer(sizes=_IMAGE_SIZES)

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "sort_order"]


# ---------------------------------------------------------------------------
# Product serializers
# ---------------------------------------------------------------------------


class ProductSerializer(serializers.ModelSerializer):
    """Catalogue / list serializer — omits full_description to keep response compact."""

    stock_status = serializers.SerializerMethodField(
        help_text="IN_STOCK | LOW_STOCK | OUT_OF_STOCK"
    )
    primary_image = serializers.SerializerMethodField(
        help_text="Hero image URL variants, or null if none is set."
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category_id",
            "price",
            "stock_quantity",
            "stock_status",
            "short_description",
            "primary_image",
        ]

    def get_stock_status(self, obj: Product) -> str:
        return _compute_stock_status(obj.stock_quantity)

    def get_primary_image(self, obj: Product):
        if obj.primary_image_id is None:
            return None
        return ProductImageSerializer(
            obj.primary_image, context=self.context
        ).data


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detail serializer — includes both description fields and full gallery."""

    stock_status = serializers.SerializerMethodField(
        help_text="IN_STOCK | LOW_STOCK | OUT_OF_STOCK"
    )
    primary_image = serializers.SerializerMethodField(
        help_text="Hero image URL variants, or null if none is set."
    )
    gallery_images = serializers.SerializerMethodField(
        help_text="All gallery images ordered by sort_order, id."
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category_id",
            "price",
            "stock_quantity",
            "stock_status",
            "short_description",
            "full_description",
            "primary_image",
            "gallery_images",
        ]

    def get_stock_status(self, obj: Product) -> str:
        return _compute_stock_status(obj.stock_quantity)

    def get_primary_image(self, obj: Product):
        if obj.primary_image_id is None:
            return None
        return ProductImageSerializer(
            obj.primary_image, context=self.context
        ).data

    def get_gallery_images(self, obj: Product):
        images = obj.images.all()
        return ProductImageSerializer(images, many=True, context=self.context).data

