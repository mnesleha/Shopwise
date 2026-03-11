from django.db import models
from django.core.exceptions import ValidationError


class OrderItem(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    quantity = models.PositiveIntegerField()
    price_at_order_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    unit_price_at_order_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    line_total_at_order_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    applied_discount_type_at_order_time = models.CharField(
        max_length=10,
        null=True,
        blank=True,
    )
    applied_discount_value_at_order_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Phase 3 pricing snapshot fields
    # These are preparation for the new pricing snapshot pipeline.
    # They are nullable to allow safe migration of existing records.
    # The order creation flow will be updated to populate them in a
    # subsequent slice once the full persistence mapping is finalised.
    # ------------------------------------------------------------------
    unit_price_net_at_order_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Net unit price captured at order time (excl. tax).",
    )
    unit_price_gross_at_order_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Gross unit price captured at order time (incl. tax, after promotion).",
    )
    tax_amount_at_order_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Per-unit tax amount captured at order time.",
    )
    tax_rate_at_order_time = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Effective tax rate percentage at order time (e.g. 23.0000 for 23 %).",
    )
    promotion_code_at_order_time = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Promotion code applied to this item at order time, if any.",
    )
    promotion_type_at_order_time = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Type of promotion applied to this item at order time, if any.",
    )
    promotion_discount_gross_at_order_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Gross discount amount from the applied promotion at order time.",
    )

    # ------------------------------------------------------------------
    # Phase 3 product + line total snapshot fields (Slice 5)
    # ------------------------------------------------------------------
    product_name_at_order_time = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Product name captured at order time. Use this for order history instead of the live product name.",
    )
    line_total_net_at_order_time = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Net line total (unit net price × quantity) captured at order time.",
    )
    line_total_gross_at_order_time = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Gross line total (unit gross price × quantity) captured at order time.",
    )

    def clean(self):
        errors = {}

        if self.quantity is None or self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero"

        # Allow zero, reject negatives for all price fields
        if self.price_at_order_time is None or self.price_at_order_time < 0:
            errors["price_at_order_time"] = "Price must be zero or greater"

        if self.unit_price_at_order_time is not None and self.unit_price_at_order_time < 0:
            errors["unit_price_at_order_time"] = "Unit price must be zero or greater"

        if self.line_total_at_order_time is not None and self.line_total_at_order_time < 0:
            errors["line_total_at_order_time"] = "Line total must be zero or greater"

        if (
            self.applied_discount_value_at_order_time is not None
            and self.applied_discount_value_at_order_time < 0
        ):
            errors["applied_discount_value_at_order_time"] = "Discount value must be zero or greater"

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"OrderItem (Order #{self.order_id}, Product #{self.product_id})"
