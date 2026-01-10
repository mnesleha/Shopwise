from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        PAID = "PAID", "Paid"
        PAYMENT_FAILED = "PAYMENT_FAILED"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELED = "CANCELED", "Canceled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    customer_email = models.EmailField(null=True, blank=True)
    customer_email_normalized = models.EmailField(
        null=True,
        blank=True,
    )
    shipping_name = models.CharField(max_length=255, null=True, blank=True)
    shipping_address_line1 = models.CharField(max_length=255, null=True, blank=True)
    shipping_address_line2 = models.CharField(max_length=255, null=True, blank=True)
    shipping_city = models.CharField(max_length=255, null=True, blank=True)
    shipping_postal_code = models.CharField(max_length=64, null=True, blank=True)
    shipping_country = models.CharField(max_length=64, null=True, blank=True)
    shipping_phone = models.CharField(max_length=64, null=True, blank=True)
    billing_same_as_shipping = models.BooleanField(default=True)
    billing_name = models.CharField(max_length=255, null=True, blank=True)
    billing_address_line1 = models.CharField(max_length=255, null=True, blank=True)
    billing_address_line2 = models.CharField(max_length=255, null=True, blank=True)
    billing_city = models.CharField(max_length=255, null=True, blank=True)
    billing_postal_code = models.CharField(max_length=64, null=True, blank=True)
    billing_country = models.CharField(max_length=64, null=True, blank=True)
    billing_phone = models.CharField(max_length=64, null=True, blank=True)
    is_claimed = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)
    claimed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claimed_orders",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        errors = {}

        # Explicit status validation (choices are validated automatically,
        # but this keeps behavior explicit and testable)
        valid_statuses = {choice.value for choice in self.Status}
        if self.status not in valid_statuses:
            errors["status"] = "Invalid order status"

        if not self.customer_email or not self.customer_email.strip():
            errors["customer_email"] = "This field is required."
        else:
            self.customer_email_normalized = self.customer_email.strip().lower()

        shipping_required_fields = [
            "shipping_name",
            "shipping_address_line1",
            "shipping_city",
            "shipping_postal_code",
            "shipping_country",
            "shipping_phone",
        ]
        for field in shipping_required_fields:
            value = getattr(self, field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors[field] = "This field is required."

        if self.billing_same_as_shipping is False:
            billing_required_fields = [
                "billing_name",
                "billing_address_line1",
                "billing_city",
                "billing_postal_code",
                "billing_country",
            ]
            for field in billing_required_fields:
                value = getattr(self, field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors[field] = "This field is required."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Order #{self.pk} ({self.status})"

    class Meta:
        indexes = [
            models.Index(
                fields=["customer_email_normalized"],
                name="orders_email_norm_idx",
            ),
            models.Index(
                fields=["is_claimed", "customer_email_normalized"],
                name="orders_claimed_email_idx",
            ),
        ]
