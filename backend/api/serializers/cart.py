from rest_framework import serializers

from carts.models import Cart, CartItem
from products.models import Product
from api.serializers.order import OrderResponseSerializer


class CartItemProductSerializer(serializers.ModelSerializer):
    """
    Minimal product representation embedded in cart responses.

    Rationale:
    - Improves frontend usability (no extra lookup required).
    - Keeps API responses self-describing for E2E tests (Postman / pytest).
    """

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = CartItemProductSerializer(read_only=True)

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


class CartCheckoutRequestSerializer(serializers.Serializer):
    customer_email = serializers.EmailField()
    shipping_name = serializers.CharField()
    shipping_address_line1 = serializers.CharField()
    shipping_address_line2 = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    shipping_city = serializers.CharField()
    shipping_postal_code = serializers.CharField()
    shipping_country = serializers.CharField()
    shipping_phone = serializers.CharField()
    billing_same_as_shipping = serializers.BooleanField(default=True)
    billing_name = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_address_line1 = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_address_line2 = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_city = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_postal_code = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_country = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_phone = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        if attrs.get("billing_same_as_shipping") is False:
            required_fields = [
                "billing_name",
                "billing_address_line1",
                "billing_city",
                "billing_postal_code",
                "billing_country",
            ]
            errors = {}
            for field in required_fields:
                value = attrs.get(field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors[field] = ["This field is required."]
            if errors:
                raise serializers.ValidationError(errors)
        return attrs


class CartCheckoutResponseSerializer(OrderResponseSerializer):
    """Checkout response shares the same contract as Orders endpoints."""
