from django.db import models
from django.core.exceptions import ValidationError


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payments",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        valid_statuses = {choice.value for choice in self.Status}
        if self.status not in valid_statuses:
            raise ValidationError({"status": "Invalid payment status"})

    def __str__(self):
        return f"Payment #{self.pk} ({self.status})"
