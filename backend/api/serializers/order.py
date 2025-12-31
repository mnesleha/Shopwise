from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from orders.models import Order
from orderitems.models import OrderItem


def _format_decimal(value: Decimal) -> str:
    quantized = Decimal(value).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    return f"{quantized:.2f}"


class OrderItemResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    product = serializers.IntegerField(source="product.id", read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    unit_price = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()

    def _line_total_decimal(self, obj: OrderItem) -> Decimal:
        if obj.line_total_at_order_time is not None:
            return obj.line_total_at_order_time
        if obj.price_at_order_time is not None:
            return obj.price_at_order_time
        return Decimal("0.00")

    def get_unit_price(self, obj: OrderItem):
        if obj.unit_price_at_order_time is not None:
            return _format_decimal(obj.unit_price_at_order_time)

        if obj.price_at_order_time is not None and obj.quantity:
            price_per_unit = obj.price_at_order_time / Decimal(obj.quantity)
            return _format_decimal(price_per_unit)

        return None

    def get_line_total(self, obj: OrderItem):
        return _format_decimal(self._line_total_decimal(obj))

    def get_discount(self, obj: OrderItem):
        discount_type = getattr(
            obj, "applied_discount_type_at_order_time", None
        )
        discount_value = getattr(
            obj, "applied_discount_value_at_order_time", None
        )

        if discount_type and discount_value is not None:
            return {
                "type": discount_type,
                "value": _format_decimal(discount_value),
            }

        return None


class OrderResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    items = OrderItemResponseSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    def get_total(self, obj: Order):
        items_field = self.fields["items"].child  # type: ignore
        total = sum(
            (
                items_field._line_total_decimal(item)
                for item in obj.items.all()
            ),
            Decimal("0.00"),
        )
        return _format_decimal(total)
