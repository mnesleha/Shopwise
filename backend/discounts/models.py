from django.db import models
from django.utils.timezone import now
from datetime import timedelta, date
from django.core.exceptions import ValidationError
from django.core.exceptions import NON_FIELD_ERRORS


def get_default_valid_from():
    return now().date()


def get_default_valid_to():
    return now().date() + timedelta(days=7)


class Discount(models.Model):
    PERCENT = "PERCENT"
    FIXED = "FIXED"

    DISCOUNT_TYPES = [
        (PERCENT, "Percent"),
        (FIXED, "Fixed"),
    ]

    name = models.CharField(max_length=255)

    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPES,
    )

    value = models.DecimalField(max_digits=5, decimal_places=2)

    valid_from = models.DateField(default=get_default_valid_from)
    valid_to = models.DateField(default=get_default_valid_to)

    is_active = models.BooleanField(default=True)

    product = models.ForeignKey(
        "products.Product",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="discounts",
    )

    category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="discounts",
    )

    def clean(self):
        errors = {}

        if self.valid_from > self.valid_to:
            errors["valid_from"] = "valid_from must be before valid_to"

        if self.value <= 0:
            errors["value"] = "Discount value must be greater than zero"

        if not self.product and not self.category:
            errors[NON_FIELD_ERRORS] = "Discount must target product or category"

        if self.product and self.category:
            errors[NON_FIELD_ERRORS] = "Discount cannot target product and category at the same time"

        if self.category and self.category.is_parent:
            errors[NON_FIELD_ERRORS] = "Discount cannot be applied to parent category"

        if errors:
            raise ValidationError(errors)

    def is_valid(self):
        today = now().date()
        return self.is_active and self.valid_from <= today <= self.valid_to

    def __str__(self):
        return self.name
