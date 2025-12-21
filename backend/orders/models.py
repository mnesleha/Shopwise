from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        PAID = "PAID", "Paid"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELED = "CANCELED", "Canceled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Explicit status validation (choices are validated automatically,
        # but this keeps behavior explicit and testable)
        valid_statuses = {choice.value for choice in self.Status}
        if self.status not in valid_statuses:
            raise ValidationError({"status": "Invalid order status"})

    def __str__(self):
        return f"Order #{self.pk} ({self.status})"
