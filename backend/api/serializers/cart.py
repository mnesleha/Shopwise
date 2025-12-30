from decimal import Decimal

from rest_framework import serializers

from carts.models import Cart, CartItem
from products.models import Product


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "quantity",
            "price_at_add_time",
        ]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "status",
            "items",
        ]


class CartItemCreateRequestSerializer(serializers.Serializer):
    """
    OpenAPI request schema for adding an item to the cart.

    This serializer is used for documentation and validation
    of the request body, not for saving data.
    """
    product_id = serializers.IntegerField(
        help_text="ID of the product to add to the cart"
    )
    quantity = serializers.IntegerField(
        min_value=1,
        help_text="Quantity must be greater than zero"
    )


class CartCheckoutItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    product = serializers.IntegerField(source="product.id", read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    price_at_order_time = serializers.SerializerMethodField()

    def get_price_at_order_time(self, obj):
        return f"{obj.price_at_order_time:.2f}"


class CartCheckoutResponseSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(source="id", read_only=True)
    status = serializers.CharField(read_only=True)
    items = CartCheckoutItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    def get_total(self, obj):
        total = sum(
            (item.price_at_order_time for item in obj.items.all()),
            Decimal("0.00"),
        )
        return f"{total:.2f}"
