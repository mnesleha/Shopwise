from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Order(models.Model):
    def _normalize_customer_email(self) -> None:
        """
        Keep customer_email_normalized consistent and non-empty whenever possible.

        NOTE:
        - We normalize early (before field validation) to avoid EmailField rejecting
        values with surrounding whitespace.
        - If customer_email is empty/whitespace, we set normalized to "" and let clean()
        raise a proper validation error for customer_email.
        """
        if self.customer_email is None:
            self.customer_email_normalized = ""
            return

        raw = str(self.customer_email)
        stripped = raw.strip()
        self.customer_email = stripped
        self.customer_email_normalized = stripped.lower()

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
        on_delete=models.SET_NULL,
    )
    customer_email = models.EmailField(null=False, blank=False)
    customer_email_normalized = models.EmailField(
        null=False,
        blank=False,
        db_index=True,
    )
    shipping_name = models.CharField(max_length=255, null=False, blank=False)
    shipping_address_line1 = models.CharField(
        max_length=255, null=False, blank=False)
    shipping_address_line2 = models.CharField(
        max_length=255, null=True, blank=True)
    shipping_city = models.CharField(max_length=255, null=False, blank=False)
    shipping_postal_code = models.CharField(
        max_length=64, null=False, blank=False)
    shipping_country = models.CharField(max_length=64, null=False, blank=False)
    shipping_phone = models.CharField(max_length=64, null=False, blank=False)
    billing_same_as_shipping = models.BooleanField(default=True)
    billing_name = models.CharField(max_length=255, null=True, blank=True)
    billing_address_line1 = models.CharField(
        max_length=255, null=True, blank=True)
    billing_address_line2 = models.CharField(
        max_length=255, null=True, blank=True)
    billing_city = models.CharField(max_length=255, null=True, blank=True)
    billing_postal_code = models.CharField(
        max_length=64, null=True, blank=True)
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
        super().clean()

        # --- customer email required + normalized ---
        if self.customer_email is None or self.customer_email.strip() == "":
            raise ValidationError(
                {"customer_email": _("customer_email is required.")})

        # Ensure normalization is consistent during validation as well
        normalized = self.customer_email.strip().lower()
        if self.customer_email_normalized is None or self.customer_email_normalized.strip() == "":
            # allow model to populate it in save(), but during full_clean we want consistency
            self.customer_email_normalized = normalized
        elif self.customer_email_normalized != normalized:
            raise ValidationError({
                "customer_email_normalized": _("customer_email_normalized must match normalized customer_email.")
            })

        expected = self.customer_email.strip().lower()
        if self.customer_email_normalized != expected:
            raise ValidationError({"customer_email_normalized": _(
                "customer_email_normalized must match normalized customer_email.")})

        # --- shipping required snapshots (shipping_phone included) ---
        required_shipping = [
            "shipping_name",
            "shipping_address_line1",
            "shipping_city",
            "shipping_postal_code",
            "shipping_country",
            "shipping_phone",
        ]
        shipping_errors = {}
        for f in required_shipping:
            v = getattr(self, f)
            if v is None or (isinstance(v, str) and v.strip() == ""):
                shipping_errors[f] = _("This field is required.")
        if shipping_errors:
            raise ValidationError(shipping_errors)

        # --- billing snapshots conditional ---
        if self.billing_same_as_shipping is False:
            required_billing = [
                "billing_name",
                "billing_address_line1",
                "billing_city",
                "billing_postal_code",
                "billing_country",
            ]
            billing_errors = {}
            for f in required_billing:
                v = getattr(self, f)
                if v is None or (isinstance(v, str) and v.strip() == ""):
                    billing_errors[f] = _(
                        "This field is required when billing_same_as_shipping is False.")
            if billing_errors:
                raise ValidationError(billing_errors)
            # billing_phone intentionally optional

        # --- claim invariants ---
        if self.is_claimed:
            if self.claimed_at is None:
                raise ValidationError(
                    {"claimed_at": _("claimed_at is required when is_claimed is True.")})
            if self.claimed_by_user_id is None:
                raise ValidationError({"claimed_by_user": _(
                    "claimed_by_user is required when is_claimed is True.")})
            if self.user_id is None:
                raise ValidationError(
                    {"user": _("user must be set when an order is claimed.")})
        else:
            if self.claimed_at is not None:
                raise ValidationError(
                    {"claimed_at": _("claimed_at must be null when is_claimed is False.")})
            if self.claimed_by_user_id is not None:
                raise ValidationError({"claimed_by_user": _(
                    "claimed_by_user must be null when is_claimed is False.")})

    def save(self, *args, **kwargs):
        self._normalize_customer_email()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.pk} ({self.status})"

    def clean_fields(self, exclude=None):
        # Normalize BEFORE Django runs field-level validation (EmailField, required fields).
        self._normalize_customer_email()
        return super().clean_fields(exclude=exclude)

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
