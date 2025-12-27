from rest_framework import serializers
from carts.models import Cart, CartItem
from products.models import Product
from api.serializers.order import OrderSerializer


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


class CartCheckoutResponseSerializer(serializers.Serializer):
    order = OrderSerializer(read_only=True)
