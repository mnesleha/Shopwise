from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone
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
        CANCELLED = "CANCELLED", "Cancelled"

    class CancelReason(models.TextChoices):
        CUSTOMER_REQUEST = "CUSTOMER_REQUEST", "Customer request"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment failed"
        PAYMENT_EXPIRED = "PAYMENT_EXPIRED", "Payment expired"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of stock"
        SHOP_REQUEST = "SHOP_REQUEST", "Shop request"
        FRAUD_SUSPECTED = "FRAUD_SUSPECTED", "Fraud suspected"
        ADMIN_CANCELLED = "ADMIN_CANCELLED", "Admin cancelled"

    class CancelledBy(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        ADMIN = "ADMIN", "Admin"
        SYSTEM = "SYSTEM", "System"

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
    cancel_reason = models.CharField(
        max_length=32,
        choices=CancelReason.choices,
        null=True,
        blank=True,
    )
    cancelled_by = models.CharField(
        max_length=16,
        choices=CancelledBy.choices,
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    guest_access_token_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
    )
    guest_access_token_created_at = models.DateTimeField(null=True, blank=True)

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
        permissions = [
            ("can_fulfill", "Can fulfill orders (ship/deliver)"),
            ("can_cancel_admin", "Can cancel orders as admin"),
        ]


class InventoryReservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        COMMITTED = "COMMITTED"
        RELEASED = "RELEASED"
        EXPIRED = "EXPIRED"

    class ReleaseReason(models.TextChoices):
        PAYMENT_FAILED = "PAYMENT_FAILED"
        PAYMENT_EXPIRED = "PAYMENT_EXPIRED"
        CUSTOMER_REQUEST = "CUSTOMER_REQUEST"
        ADMIN_CANCEL = "ADMIN_CANCEL"
        OUT_OF_STOCK = "OUT_OF_STOCK"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="inventory_reservations",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="inventory_reservations",
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    expires_at = models.DateTimeField()
    committed_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    release_reason = models.CharField(
        max_length=32,
        choices=ReleaseReason.choices,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE

    @property
    def is_expired(self) -> bool:
        return self.status == self.Status.ACTIVE and self.expires_at < timezone.now()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="inventory_reservation_order_product_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "expires_at"],
                name="inv_res_status_exp_idx",
            ),
        ]
