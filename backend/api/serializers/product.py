from django.conf import settings
from rest_framework import serializers

from products.models import Product

# ---------------------------------------------------------------------------
# Stock status constants
# ---------------------------------------------------------------------------

IN_STOCK = "IN_STOCK"
LOW_STOCK = "LOW_STOCK"
OUT_OF_STOCK = "OUT_OF_STOCK"

_STOCK_STATUS_CHOICES = [IN_STOCK, LOW_STOCK, OUT_OF_STOCK]


def _compute_stock_status(stock_quantity: int) -> str:
    threshold: int = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
    if stock_quantity <= 0:
        return OUT_OF_STOCK
    if stock_quantity <= threshold:
        return LOW_STOCK
    return IN_STOCK


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


class ProductSerializer(serializers.ModelSerializer):
    """Catalogue / list serializer — omits full_description to keep response compact."""

    stock_status = serializers.SerializerMethodField(
        help_text="IN_STOCK | LOW_STOCK | OUT_OF_STOCK"
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
        ]

    def get_stock_status(self, obj: Product) -> str:
        return _compute_stock_status(obj.stock_quantity)


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detail serializer — includes both description fields."""

    stock_status = serializers.SerializerMethodField(
        help_text="IN_STOCK | LOW_STOCK | OUT_OF_STOCK"
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
        ]

    def get_stock_status(self, obj: Product) -> str:
        return _compute_stock_status(obj.stock_quantity)
