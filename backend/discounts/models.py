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


# ---------------------------------------------------------------------------
# Phase 2 — Line-level promotion domain model
# ---------------------------------------------------------------------------


class PromotionType(models.TextChoices):
    PERCENT = "PERCENT", "Percent"
    FIXED = "FIXED", "Fixed"


class Promotion(models.Model):
    """Business-defined line-level promotion.

    A Promotion captures the *definition* of a discount rule (what discount
    to apply and when).  Which products or categories are targeted is stored
    separately via ``PromotionProduct`` and ``PromotionCategory``.

    Resolution (applying the promotion to a price) intentionally lives outside
    this model and will be introduced in a later slice.
    """

    name = models.CharField(
        max_length=255,
        help_text="Human-readable promotion name visible in admin reports.",
    )
    code = models.CharField(
        max_length=64,
        unique=True,
        help_text="Stable machine-readable identifier, e.g. 'summer-2026'. "
        "Used for logging and future coupon linkage.",
    )
    type = models.CharField(
        max_length=10,
        choices=PromotionType.choices,
        help_text="PERCENT — relative discount (e.g. 10 %); FIXED — absolute amount off.",
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Discount magnitude. For PERCENT: 0 < value ≤ 100. For FIXED: value > 0.",
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Higher value = higher priority. Used for conflict resolution in later phases.",
    )
    is_active = models.BooleanField(default=True)
    active_from = models.DateField(
        null=True,
        blank=True,
        help_text="Optional start date (inclusive). If blank, promotion is always eligible from the past.",
    )
    active_to = models.DateField(
        null=True,
        blank=True,
        help_text="Optional end date (inclusive). If blank, promotion has no expiry.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional internal notes visible to admin users only.",
    )

    class Meta:
        ordering = ["-priority", "name"]
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def clean(self) -> None:
        errors: dict = {}

        if self.value is not None and self.value <= 0:
            errors["value"] = "Promotion value must be greater than zero."

        if (
            self.type == PromotionType.PERCENT
            and self.value is not None
            and self.value > 100
        ):
            errors["value"] = "Percent promotion value cannot exceed 100."

        if self.active_from and self.active_to and self.active_from > self.active_to:
            errors["active_from"] = "active_from must not be later than active_to."

        if errors:
            raise ValidationError(errors)

    def is_currently_active(self) -> bool:
        """Return True when this promotion is active and within its optional date window."""
        if not self.is_active:
            return False
        today = now().date()
        if self.active_from and today < self.active_from:
            return False
        if self.active_to and today > self.active_to:
            return False
        return True


class PromotionProduct(models.Model):
    """Targeting record linking a Promotion to a specific Product.

    Using an explicit through-table instead of a plain ManyToManyField gives
    a natural admin entry-point and a place to add future per-target metadata
    (e.g. override value, notes).
    """

    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name="product_targets",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="promotion_targets",
    )

    class Meta:
        unique_together = [("promotion", "product")]
        verbose_name = "Promotion → Product"
        verbose_name_plural = "Promotion → Products"

    def __str__(self) -> str:
        return f"{self.promotion.code} → {self.product}"


class PromotionCategory(models.Model):
    """Targeting record linking a Promotion to a Category.

    See ``PromotionProduct`` docstring for rationale of the explicit table.
    """

    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name="category_targets",
    )
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.CASCADE,
        related_name="promotion_targets",
    )

    class Meta:
        unique_together = [("promotion", "category")]
        verbose_name = "Promotion → Category"
        verbose_name_plural = "Promotion → Categories"

    def __str__(self) -> str:
        return f"{self.promotion.code} → {self.category}"
