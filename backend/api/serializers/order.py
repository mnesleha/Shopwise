from rest_framework import serializers
from decimal import Decimal
from orders.models import Order
from orderitems.models import OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "quantity",
            "price_at_order_time",
            "total_price",
        ]

    def get_total_price(self, obj):
        total = obj.price_at_order_time * obj.quantity
        return f"{total:.2f}"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "status", "items", "total_price"]

    def get_total_price(self, obj):
        total = sum(
            (item.price_at_order_time * item.quantity for item in obj.items.all()),
            Decimal("0.00"),
        )
        return f"{total:.2f}"
