from django.db import models
from django.core.exceptions import ValidationError


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def clean(self):
        errors = {}

        # Name validation
        if not self.name:
            errors["name"] = "Product name cannot be empty"

        # Price validation
        if self.price is not None and self.price <= 0:
            errors["price"] = "Product price must be greater than zero"

        # Stock validation
        if self.stock_quantity is not None and self.stock_quantity < 0:
            errors["stock_quantity"] = "Stock quantity cannot be negative"

        if errors:
            raise ValidationError(errors)

    def is_sellable(self) -> bool:
        return self.is_active and self.stock_quantity > 0

    def __str__(self):
        return self.name
