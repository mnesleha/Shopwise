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

    def clean(self):
        errors = {}

        if self.quantity is None or self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero"

        if self.price_at_order_time is None or self.price_at_order_time <= 0:
            errors["price_at_order_time"] = "Price must be greater than zero"

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"OrderItem (Order #{self.order_id}, Product #{self.product_id})"
