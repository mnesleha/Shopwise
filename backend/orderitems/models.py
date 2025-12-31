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

    def clean(self):
        errors = {}

        if self.quantity is None or self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero"

        # Allow zero, reject negatives for all price fields
        if (
            self.price_at_order_time is None
            or self.price_at_order_time < 0
        ):
            errors["price_at_order_time"] = (
                "Price must be zero or greater"
            )

        if (
            self.unit_price_at_order_time is not None
            and self.unit_price_at_order_time < 0
        ):
            errors["unit_price_at_order_time"] = (
                "Unit price must be zero or greater"
            )

        if (
            self.line_total_at_order_time is not None
            and self.line_total_at_order_time < 0
        ):
            errors["line_total_at_order_time"] = (
                "Line total must be zero or greater"
            )

        if (
            self.applied_discount_value_at_order_time is not None
            and self.applied_discount_value_at_order_time < 0
        ):
            errors["applied_discount_value_at_order_time"] = (
                "Discount value must be zero or greater"
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"OrderItem (Order #{self.order_id}, "
            f"Product #{self.product_id})"
        )
