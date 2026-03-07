from rest_framework import serializers
from products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    """Catalogue / list serializer — omits full_description to keep response compact."""

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category_id",
            "price",
            "stock_quantity",
            "short_description",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detail serializer — includes both description fields."""

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category_id",
            "price",
            "stock_quantity",
            "short_description",
            "full_description",
        ]
