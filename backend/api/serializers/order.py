from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from discounts.models import PromotionType
from discounts.services.order_discount_allocation import (
    OrderDiscountInput,
    OrderLineInput,
    allocate_order_discount,
)
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
    # Phase 3 order-level totals snapshot (legacy names kept for backward compat)
    subtotal_net = serializers.SerializerMethodField()
    subtotal_gross = serializers.SerializerMethodField()
    total_tax = serializers.SerializerMethodField()
    total_discount = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    # VAT breakdown grouped by tax rate — backend-owned for FE invoice rendering
    vat_breakdown = serializers.SerializerMethodField()
    # Phase 4 — explicit pre/post order-discount fields for FE accounting truth.
    # These replace the ambiguously-named snapshot fields above for any UI that
    # needs to distinguish pre- and post-order-discount values.
    order_discount_gross = serializers.SerializerMethodField()
    pre_order_discount_subtotal_gross = serializers.SerializerMethodField()
    post_order_discount_subtotal_net = serializers.SerializerMethodField()
    post_order_discount_total_tax = serializers.SerializerMethodField()
    post_order_discount_total_gross = serializers.SerializerMethodField()
    # Business address snapshot fields — shipping and billing nested objects.
    # Both include company / company_id / vat_id when present.
    shipping_address = serializers.SerializerMethodField()
    billing_address = serializers.SerializerMethodField()
    shipping_method = serializers.SerializerMethodField()
    # Contact email captured at checkout.
    customer_email = serializers.CharField(read_only=True)
    # Supplier snapshot — populated from stored order truth (immutable after order creation).
    # Returns None for pre-supplier orders (orders created before this feature was deployed).
    supplier = serializers.SerializerMethodField()

    def get_created_at(self, obj: Order) -> str | None:
        if obj.created_at:
            return obj.created_at.isoformat()
        return None

    def get_total(self, obj: Order) -> str:
        # post_order_discount_total_gross = subtotal_gross after applying OD
        # (when OD exists, subtotal_gross is already post-OD).
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

    # ------------------------------------------------------------------
    # Phase 4: explicit pre/post order-discount fields
    # ------------------------------------------------------------------

    def get_order_discount_gross(self, obj: Order) -> str | None:
        """Gross order-level discount applied at checkout.

        Null when no order-level discount was applied.
        This is the *order-level* discount only — does not include
        per-item line discounts (see total_discount for the combined total).
        """
        return _format_decimal_or_none(obj.order_discount_gross)

    def get_pre_order_discount_subtotal_gross(self, obj: Order) -> str | None:
        """Gross subtotal incl. VAT after line discounts, BEFORE order-level discount.

        This is the customer-visible "subtotal" that serves as the basis for
        the order-level discount deduction.  Derivation:
            pre_order_discount_subtotal_gross = subtotal_gross + order_discount_gross

        When no order-level discount exists, equals subtotal_gross (= final total).
        Null for legacy orders that lack the Phase 3 snapshot.
        """
        if obj.subtotal_gross is None:
            return None
        order_discount = (
            Decimal(str(obj.order_discount_gross))
            if obj.order_discount_gross is not None
            else Decimal("0.00")
        )
        return _format_decimal(Decimal(str(obj.subtotal_gross)) + order_discount)

    def get_post_order_discount_subtotal_net(self, obj: Order) -> str | None:
        """Net subtotal (tax base) after ALL discounts — the final accounting net.

        Aliases subtotal_net.  Null for legacy orders.
        """
        return _format_decimal_or_none(obj.subtotal_net)

    def get_post_order_discount_total_tax(self, obj: Order) -> str | None:
        """Total VAT after ALL discounts — consistent with the VAT breakdown totals.

        Aliases total_tax.  Null for legacy orders.
        """
        return _format_decimal_or_none(obj.total_tax)

    def get_post_order_discount_total_gross(self, obj: Order) -> str | None:
        """Final gross total (incl. VAT) after ALL discounts — the amount the customer pays.

        Aliases subtotal_gross (which stores the post-order-discount gross in the
        checkout pipeline).  Null for legacy orders; fall back to total field.
        """
        return _format_decimal_or_none(obj.subtotal_gross)

    def get_vat_breakdown(self, obj: Order) -> list:
        """Return VAT breakdown grouped by tax rate.

        When an order-level discount is present (order_discount_gross != null),
        values reflect the *post-order-discount* allocation truth: the discount
        is proportionally distributed across VAT-rate buckets via the
        allocate_order_discount engine, so that tax_base, vat_amount and
        total_incl_vat per bucket are accounting-correct after the deduction.

        When no order-level discount exists, each bucket is simply the sum of
        pre-discount (post-line-promotion) item line totals for that rate.

        Only items with fully-populated Phase 3 snapshot fields are included.
        Items without line_total_net or line_total_gross snapshots are skipped.
        """
        _ZERO = Decimal("0")

        # Collect items with full Phase 3 snapshot fields.
        items_with_snapshots = [
            item
            for item in obj.items.all()
            if (
                item.line_total_net_at_order_time is not None
                and item.line_total_gross_at_order_time is not None
            )
        ]

        if not items_with_snapshots:
            return []

        # When order-level discount exists, use the allocation engine to obtain
        # post-discount per-bucket accounting truth.
        if (
            obj.order_discount_gross is not None
            and obj.order_discount_gross > _ZERO
            and obj.currency
        ):
            lines = [
                OrderLineInput(
                    line_net=Decimal(str(item.line_total_net_at_order_time)),
                    line_gross=Decimal(str(item.line_total_gross_at_order_time)),
                    tax_rate=(
                        Decimal(str(item.tax_rate_at_order_time))
                        if item.tax_rate_at_order_time is not None
                        else _ZERO
                    ),
                    currency=obj.currency,
                )
                for item in items_with_snapshots
            ]
            discount = OrderDiscountInput(
                type=PromotionType.FIXED,
                value=Decimal(str(obj.order_discount_gross)),
                currency=obj.currency,
            )
            result = allocate_order_discount(lines=lines, discount=discount)
            return [
                {
                    "tax_rate": _format_decimal(bucket.tax_rate),
                    "tax_base": _format_decimal(bucket.adjusted_net),
                    "vat_amount": _format_decimal(bucket.adjusted_tax),
                    "total_incl_vat": _format_decimal(bucket.adjusted_gross),
                }
                for bucket in result.buckets
            ]

        # No order-level discount: group item line totals directly.
        groups: dict[str, dict] = defaultdict(
            lambda: {"tax_base": _ZERO, "vat_amount": _ZERO, "total_incl_vat": _ZERO}
        )

        for item in items_with_snapshots:
            rate_raw = (
                item.tax_rate_at_order_time
                if item.tax_rate_at_order_time is not None
                else _ZERO
            )
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
    def get_shipping_address(self, obj: Order) -> dict:
        """Full shipping address snapshot including business fields.

        Returns a consistent dict for all orders; business fields default to
        empty string for legacy orders where the fields were not captured.
        """
        return {
            "first_name": obj.shipping_first_name or "",
            "last_name": obj.shipping_last_name or "",
            "name": f"{obj.shipping_first_name or ''} {obj.shipping_last_name or ''}".strip(),
            "address_line1": obj.shipping_address_line1 or "",
            "address_line2": obj.shipping_address_line2 or "",
            "city": obj.shipping_city or "",
            "postal_code": obj.shipping_postal_code or "",
            "country": obj.shipping_country or "",
            "phone": obj.shipping_phone or "",
            "company": obj.shipping_company or "",
            "company_id": obj.shipping_company_id or "",
            "vat_id": obj.shipping_vat_id or "",
        }

    def get_billing_address(self, obj: Order) -> dict | None:
        """Full billing address snapshot including business fields.

        Returns None when billing_same_as_shipping is True, indicating the
        caller should fall back to shipping_address for billing display.
        Returns a dict when a distinct billing address was captured.
        Business fields default to empty string for legacy orders.
        """
        if obj.billing_same_as_shipping:
            return None
        return {
            "first_name": obj.billing_first_name or "",
            "last_name": obj.billing_last_name or "",
            "name": f"{obj.billing_first_name or ''} {obj.billing_last_name or ''}".strip(),
            "address_line1": obj.billing_address_line1 or "",
            "address_line2": obj.billing_address_line2 or "",
            "city": obj.billing_city or "",
            "postal_code": obj.billing_postal_code or "",
            "country": obj.billing_country or "",
            "phone": obj.billing_phone or "",
            "company": obj.billing_company or "",
            "company_id": obj.billing_company_id or "",
            "vat_id": obj.billing_vat_id or "",
        }

    def get_shipping_method(self, obj: Order) -> dict | None:
        if not obj.shipping_provider_code or not obj.shipping_service_code:
            return None

        return {
            "provider_code": obj.shipping_provider_code,
            "service_code": obj.shipping_service_code,
            "name": obj.shipping_method_name or "",
        }

    def get_supplier(self, obj: Order) -> dict | None:
        """Return supplier snapshot from stored order truth.

        Returns a structured supplier block for invoice / order detail rendering.
        All fields are read from the order's immutable snapshot — they reflect
        the supplier configuration at order creation time and do NOT change when
        the supplier is later updated in Django admin.

        Returns None for pre-supplier orders (orders created before this feature
        was deployed) where no snapshot was captured.
        """
        # If no supplier name was snapshotted this is a pre-supplier order.
        if not obj.supplier_name:
            return None

        return {
            # Identity
            "name": obj.supplier_name or "",
            "company_id": obj.supplier_company_id or "",
            "vat_id": obj.supplier_vat_id or "",
            "email": obj.supplier_email or "",
            "phone": obj.supplier_phone or "",
            # Address
            "street_line_1": obj.supplier_street_line_1 or "",
            "street_line_2": obj.supplier_street_line_2 or "",
            "city": obj.supplier_city or "",
            "postal_code": obj.supplier_postal_code or "",
            "country": obj.supplier_country or "",
            # Payment
            "bank_name": obj.supplier_bank_name or "",
            "account_number": obj.supplier_account_number or "",
            "iban": obj.supplier_iban or "",
            "swift": obj.supplier_swift or "",
        }