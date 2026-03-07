from django.db import models
from django.core.exceptions import ValidationError

from utils.sanitize import sanitize_markdown


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey("categories.Category", null=True, blank=True, on_delete=models.SET_NULL, related_name="products")

    # Plain-text teaser shown in catalogue cards and the detail header.
    short_description = models.TextField(blank=True, default="")

    # Full product description in Markdown, rendered on the detail page.
    full_description = models.TextField(blank=True, default="")

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

    def save(self, *args, **kwargs):
        # Strip raw HTML from the Markdown description before persisting.
        # Applies to all entry points: admin, API, management commands.
        self.full_description = sanitize_markdown(self.full_description)
        super().save(*args, **kwargs)

    def is_sellable(self) -> bool:
        return self.is_active and self.stock_quantity > 0

    def __str__(self):
        return self.name
