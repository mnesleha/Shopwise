from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now


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

    value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    # Targets (exactly one must be set)
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

        # Date range validation
        if self.valid_from and self.valid_to:
            if self.valid_from > self.valid_to:
                errors["valid_from"] = "valid_from must be before valid_to"

        # Value validation
        if self.value is not None and self.value <= 0:
            errors["value"] = "Discount value must be greater than zero"

        # Target validation (XOR)
        if not self.product and not self.category:
            errors["target"] = "Discount must target product or category"

        if self.product and self.category:
            errors["target"] = "Discount cannot target product and category at the same time"

        if errors:
            raise ValidationError(errors)

    def is_valid(self) -> bool:
        if not self.is_active:
            return False

        current_time = now()
        return self.valid_from <= current_time <= self.valid_to

    def __str__(self):
        return self.name
