from rest_framework import serializers
from discounts.models import Discount
from products.models import Product


class DiscountProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name"]


class DiscountSerializer(serializers.ModelSerializer):
    product = DiscountProductSerializer(read_only=True)

    class Meta:
        model = Discount
        fields = [
            "id",
            "discount_type",
            "value",
            "product",
        ]
