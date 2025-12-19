from django.db import models
from django.utils.timezone import now

# Create your models here.


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
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def is_valid(self) -> bool:
        current_time = now()
        return (
            self.is_active
            and self.valid_from <= current_time <= self.valid_to
        )

    def __str__(self):
        return self.name
