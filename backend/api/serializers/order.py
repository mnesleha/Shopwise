from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from orders.models import Order
from orderitems.models import OrderItem


def _format_decimal(value: Decimal) -> str:
    return f"{Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def _format_decimal_or_none(value) -> str | None:
    if value is None:
        return None
    return _format_decimal(Decimal(str(value)))


def _line_total_gross_decimal(obj: OrderItem) -> Decimal:
    """Return the gross line total, preferring the new snapshot field."""
    if obj.line_total_gross_at_order_time is not None:
        return obj.line_total_gross_at_order_time
    if obj.line_total_at_order_time is not None:
        return obj.line_total_at_order_time
    if obj.price_at_order_time is not None:
        return obj.price_at_order_time
    return Decimal("0.00")


class OrderItemResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    product = serializers.IntegerField(source="product.id", read_only=True)
    # Snapshot name; falls back to live product name for records created before
    # Phase 3 Slice 5.
    product_name = serializers.SerializerMethodField()
    quantity = serializers.IntegerField(read_only=True)
    # Legacy gross unit price (kept for backward compatibility)
    unit_price = serializers.SerializerMethodField()
    # Explicit net / gross unit price snapshot fields for invoice rendering
    unit_price_net = serializers.SerializerMethodField()
    unit_price_gross = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    tax_rate = serializers.SerializerMethodField()
    # Legacy gross line total (kept for backward compatibility)
    line_total = serializers.SerializerMethodField()
    # Explicit net / gross line total snapshot fields for invoice rendering
    line_total_net = serializers.SerializerMethodField()
    line_total_gross = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()

    def get_product_name(self, obj: OrderItem) -> str:
        if obj.product_name_at_order_time:
            return obj.product_name_at_order_time
        # Fallback: live product name (pre-snapshot orders or unmigrated data)
        return getattr(obj.product, "name", f"Product #{obj.product_id}")

    def get_unit_price(self, obj: OrderItem) -> str | None:
        if obj.unit_price_at_order_time is not None:
            return _format_decimal(obj.unit_price_at_order_time)
        if obj.price_at_order_time is not None and obj.quantity and obj.quantity > 0:
            return _format_decimal(obj.price_at_order_time / Decimal(obj.quantity))
        return None

    def get_unit_price_net(self, obj: OrderItem) -> str | None:
        return _format_decimal_or_none(obj.unit_price_net_at_order_time)

    def get_unit_price_gross(self, obj: OrderItem) -> str | None:
        # Prefer explicit gross snapshot; fall back to legacy unit_price
        if obj.unit_price_gross_at_order_time is not None:
            return _format_decimal(obj.unit_price_gross_at_order_time)
        return self.get_unit_price(obj)

    def get_tax_amount(self, obj: OrderItem) -> str | None:
        return _format_decimal_or_none(obj.tax_amount_at_order_time)

    def get_tax_rate(self, obj: OrderItem) -> str | None:
        return _format_decimal_or_none(obj.tax_rate_at_order_time)

    def get_line_total(self, obj: OrderItem) -> str:
        return _format_decimal(_line_total_gross_decimal(obj))

    def get_line_total_net(self, obj: OrderItem) -> str | None:
        return _format_decimal_or_none(obj.line_total_net_at_order_time)

    def get_line_total_gross(self, obj: OrderItem) -> str:
        return _format_decimal(_line_total_gross_decimal(obj))

    def get_discount(self, obj: OrderItem) -> dict | None:
        discount_type = getattr(obj, "applied_discount_type_at_order_time", None)
        discount_value = getattr(obj, "applied_discount_value_at_order_time", None)
        if discount_type and discount_value is not None:
            return {
                "type": discount_type,
                "value": _format_decimal(discount_value),
            }
        return None


class OrderResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    created_at = serializers.SerializerMethodField()
    items = OrderItemResponseSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    # Phase 3 order-level totals snapshot
    subtotal_net = serializers.SerializerMethodField()
    subtotal_gross = serializers.SerializerMethodField()
    total_tax = serializers.SerializerMethodField()
    total_discount = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    # VAT breakdown grouped by tax rate — backend-owned for FE invoice rendering
    vat_breakdown = serializers.SerializerMethodField()

    def get_created_at(self, obj: Order) -> str | None:
        if obj.created_at:
            return obj.created_at.isoformat()
        return None

    def get_total(self, obj: Order) -> str:
        if obj.subtotal_gross is not None:
            return _format_decimal(obj.subtotal_gross)
        total = sum(
            (_line_total_gross_decimal(item) for item in obj.items.all()),
            Decimal("0.00"),
        )
        return _format_decimal(total)

    def get_subtotal_net(self, obj: Order) -> str | None:
        return _format_decimal_or_none(obj.subtotal_net)

    def get_subtotal_gross(self, obj: Order) -> str | None:
        return _format_decimal_or_none(obj.subtotal_gross)

    def get_total_tax(self, obj: Order) -> str | None:
        return _format_decimal_or_none(obj.total_tax)

    def get_total_discount(self, obj: Order) -> str | None:
        return _format_decimal_or_none(obj.total_discount)

    def get_currency(self, obj: Order) -> str | None:
        return obj.currency

    def get_vat_breakdown(self, obj: Order) -> list:
        """Return VAT breakdown grouped by tax rate.

        Each entry contains:
          tax_rate      — percentage string, e.g. "10.00"
          tax_base      — sum of net line totals for this rate
          vat_amount    — sum of (gross - net) line amounts for this rate
          total_incl_vat — sum of gross line totals for this rate

        Only items with fully-populated Phase 3 snapshot fields are included.
        Items without line_total_net or line_total_gross snapshots are skipped
        (pre-snapshot records or unmigrated products).
        """
        # Use Decimal accumulators per rate to avoid float precision issues.
        _ZERO = Decimal("0")
        groups: dict[str, dict] = defaultdict(
            lambda: {"tax_base": _ZERO, "vat_amount": _ZERO, "total_incl_vat": _ZERO}
        )

        for item in obj.items.all():
            if (
                item.line_total_net_at_order_time is None
                or item.line_total_gross_at_order_time is None
            ):
                continue

            rate_raw = item.tax_rate_at_order_time if item.tax_rate_at_order_time is not None else _ZERO
            rate_key = _format_decimal(Decimal(str(rate_raw)))

            line_net = Decimal(str(item.line_total_net_at_order_time))
            line_gross = Decimal(str(item.line_total_gross_at_order_time))
            groups[rate_key]["tax_base"] += line_net
            groups[rate_key]["vat_amount"] += line_gross - line_net
            groups[rate_key]["total_incl_vat"] += line_gross

        return [
            {
                "tax_rate": rate,
                "tax_base": _format_decimal(g["tax_base"]),
                "vat_amount": _format_decimal(g["vat_amount"]),
                "total_incl_vat": _format_decimal(g["total_incl_vat"]),
            }
            for rate, g in sorted(groups.items(), key=lambda x: Decimal(x[0]))
        ]
