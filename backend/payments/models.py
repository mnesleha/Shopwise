from django.db import models
from django.core.exceptions import ValidationError

from products.models import CURRENCY_CHOICES


class Payment(models.Model):
    """Represents a single payment attempt for an order.

    Design notes:
    - ``payment_method`` is business-facing (what the customer chose, e.g. CARD).
    - ``provider`` is technical (which backend processed it, e.g. DEV_FAKE).
    - Provider metadata fields (``provider_payment_id``, ``provider_reference``)
      are reserved for future hosted-gateway flows and are null in the current
      dev/fake path.
    - ``amount`` and ``currency`` are snapshots captured at payment creation time.
    - ``paid_at`` / ``failed_at`` / ``failure_reason`` support audit and retry logic
      without querying order state.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    class PaymentMethod(models.TextChoices):
        CARD = "CARD", "Card"
        COD = "COD", "Cash on Delivery"

    class Provider(models.TextChoices):
        # Current development / simulation provider.
        DEV_FAKE = "DEV_FAKE", "Dev Fake (simulation)"
        # Future providers will be added here without touching existing data.

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

    # Business-facing method chosen by the customer.
    # Nullable for backward compatibility with pre-expansion payment records.
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        null=True,
        blank=True,
    )

    # Technical provider that processed (or will process) this payment.
    provider = models.CharField(
        max_length=50,
        choices=Provider.choices,
        default=Provider.DEV_FAKE,
    )

    # External reference assigned by the payment provider (e.g. gateway transaction ID).
    # Null until a real provider populates it.
    provider_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # Internal reference used when communicating with the provider (e.g. idempotency key).
    provider_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # Monetary snapshot at payment creation time.
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        null=True,
        blank=True,
    )

    # Outcome timestamps — set by the service layer when final status is known.
    paid_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    # Human-readable failure reason for operator visibility and retry decisions.
    failure_reason = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        valid_statuses = {choice.value for choice in self.Status}
        if self.status not in valid_statuses:
            raise ValidationError({"status": "Invalid payment status"})

        valid_methods = {choice.value for choice in self.PaymentMethod}
        if self.payment_method and self.payment_method not in valid_methods:
            raise ValidationError({"payment_method": "Invalid payment method"})

        valid_providers = {choice.value for choice in self.Provider}
        if self.provider and self.provider not in valid_providers:
            raise ValidationError({"provider": "Invalid payment provider"})

    def __str__(self):
        return f"Payment #{self.pk} ({self.status})"
