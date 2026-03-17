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


class PromotionAmountScope(models.TextChoices):
    NET = "NET", "Net (base price before tax)"
    GROSS = "GROSS", "Gross (final customer-visible price)"


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
    amount_scope = models.CharField(
        max_length=5,
        choices=PromotionAmountScope.choices,
        default=PromotionAmountScope.GROSS,
        help_text=(
            "For FIXED promotions only: whether the fixed amount is deducted from the "
            "NET price (base before tax) or the GROSS price (final price the customer sees). "
            "Defaults to GROSS (B2C-friendly). Ignored for PERCENT promotions."
        ),
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


# ---------------------------------------------------------------------------
# Phase 4 / Slice 1 — Order-level discount domain model
# ---------------------------------------------------------------------------


class AcquisitionMode(models.TextChoices):
    """How an order-level promotion reaches the customer.

    AUTO_APPLY      — platform applies automatically (on-site promos, threshold rewards).
    CAMPAIGN_APPLY  — applied via campaign context (email link, UTM, URL token, account bound).
    MANUAL_ENTRY    — customer types a coupon code at checkout (fallback mechanism only).
    """

    AUTO_APPLY = "AUTO_APPLY", "Auto-apply"
    CAMPAIGN_APPLY = "CAMPAIGN_APPLY", "Campaign apply"
    MANUAL_ENTRY = "MANUAL_ENTRY", "Manual entry"


class StackingPolicy(models.TextChoices):
    """Controlled stacking policy for order-level discounts.

    EXCLUSIVE              — this order-level discount cannot coexist with any other
                             order-level discount on the same order.
    STACKABLE_WITH_LINE    — can coexist with line-level promotions, but still exclusive
                             among order-level discounts (only one order-level active at a time).

    Unlimited stacking is intentionally not available in this slice.
    """

    EXCLUSIVE = "EXCLUSIVE", "Exclusive (no other order-level discounts)"
    STACKABLE_WITH_LINE = "STACKABLE_WITH_LINE", "Stackable with line-level promotions"


class OrderPromotion(models.Model):
    """Order-level promotion definition.

    Represents a discount that applies to the whole order rather than individual
    line items.  Covers four reference scenarios:

    1. On-site auto-applied order discount   (acquisition_mode=AUTO_APPLY)
    2. Threshold / progress reward            (acquisition_mode=AUTO_APPLY, minimum_order_value set)
    3. Campaign-applied offer                 (acquisition_mode=CAMPAIGN_APPLY)
    4. Owned-media contextual promotion       (is_discoverable=True, any acquisition_mode)

    The VAT allocation engine is intentionally *not* part of this slice.
    """

    name = models.CharField(
        max_length=255,
        help_text="Human-readable promotion name visible in admin and customer-facing messages.",
    )
    code = models.CharField(
        max_length=64,
        unique=True,
        help_text="Stable machine-readable identifier used for logging and offer linkage.",
    )
    type = models.CharField(
        max_length=10,
        choices=PromotionType.choices,
        help_text="PERCENT — relative discount; FIXED — absolute amount off.",
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Discount magnitude.  PERCENT: 0 < value ≤ 100.  FIXED: value > 0.",
    )
    acquisition_mode = models.CharField(
        max_length=16,
        choices=AcquisitionMode.choices,
        default=AcquisitionMode.AUTO_APPLY,
        help_text=(
            "AUTO_APPLY: platform applies automatically. "
            "CAMPAIGN_APPLY: triggered by campaign context (URL/UTM/email). "
            "MANUAL_ENTRY: customer enters a coupon code (fallback only)."
        ),
    )
    stacking_policy = models.CharField(
        max_length=22,
        choices=StackingPolicy.choices,
        default=StackingPolicy.EXCLUSIVE,
        help_text=(
            "Controls coexistence with other discounts on the same order. "
            "See StackingPolicy docstring for semantics."
        ),
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Higher value = higher priority.  Used for conflict resolution.",
    )
    minimum_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Optional minimum gross order value (before this discount) required for eligibility. "
            "Used for threshold / progress-reward scenarios."
        ),
    )
    is_active = models.BooleanField(default=True)
    active_from = models.DateField(
        null=True,
        blank=True,
        help_text="Optional start date (inclusive).  Blank = no lower bound.",
    )
    active_to = models.DateField(
        null=True,
        blank=True,
        help_text="Optional end date (inclusive).  Blank = no expiry.",
    )
    is_discoverable = models.BooleanField(
        default=False,
        help_text=(
            "When True, this promotion can be surfaced in-product as an active benefit "
            "(owned-media contextual promotion / messaging hook). "
            "Does not affect eligibility logic."
        ),
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional internal notes or customer-facing benefit description.",
    )

    class Meta:
        ordering = ["-priority", "name"]
        verbose_name = "Order Promotion"
        verbose_name_plural = "Order Promotions"

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

        if self.minimum_order_value is not None and self.minimum_order_value <= 0:
            errors["minimum_order_value"] = "minimum_order_value must be greater than zero."

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


class OfferStatus(models.TextChoices):
    """Lifecycle status of a coupon / offer token.

    CREATED    — offer has been generated but not yet delivered to a recipient.
    DELIVERED  — offer was sent / surfaced to the intended recipient.
    CLAIMED    — recipient has acknowledged / added the offer (pre-checkout).
    REDEEMED   — offer was successfully applied at checkout.
    EXPIRED    — offer passed its active window or was invalidated without being redeemed.
    """

    CREATED = "CREATED", "Created"
    DELIVERED = "DELIVERED", "Delivered"
    CLAIMED = "CLAIMED", "Claimed"
    REDEEMED = "REDEEMED", "Redeemed"
    EXPIRED = "EXPIRED", "Expired"


class Offer(models.Model):
    """Coupon / offer token entity.

    Represents a concrete, distributable instance of an OrderPromotion.
    Used for CAMPAIGN_APPLY and MANUAL_ENTRY acquisition modes.

    AUTO_APPLY promotions do not require Offer records — they are applied
    automatically without a token.
    """

    token = models.CharField(
        max_length=64,
        unique=True,
        help_text=(
            "The customer-facing code or internal campaign token.  "
            "Must be non-empty.  For MANUAL_ENTRY this is what the customer types."
        ),
    )
    promotion = models.ForeignKey(
        OrderPromotion,
        on_delete=models.PROTECT,
        related_name="offers",
        help_text="The order-level promotion this offer grants access to.",
    )
    status = models.CharField(
        max_length=10,
        choices=OfferStatus.choices,
        default=OfferStatus.CREATED,
        help_text="Lifecycle status of this offer token.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Master switch.  Inactive offers are not eligible regardless of status.",
    )
    active_from = models.DateField(
        null=True,
        blank=True,
        help_text="Optional start date (inclusive).  Blank = no lower bound.",
    )
    active_to = models.DateField(
        null=True,
        blank=True,
        help_text="Optional end date (inclusive).  Blank = no expiry.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional internal notes or distribution context.",
    )

    class Meta:
        ordering = ["token"]
        verbose_name = "Offer"
        verbose_name_plural = "Offers"

    def __str__(self) -> str:
        return f"{self.token} → {self.promotion.code}"

    def clean(self) -> None:
        errors: dict = {}

        if not self.token or not self.token.strip():
            errors["token"] = "Offer token must not be blank."

        if self.active_from and self.active_to and self.active_from > self.active_to:
            errors["active_from"] = "active_from must not be later than active_to."

        if errors:
            raise ValidationError(errors)

    def is_currently_active(self) -> bool:
        """Return True when this offer is active and within its optional date window."""
        if not self.is_active:
            return False
        today = now().date()
        if self.active_from and today < self.active_from:
            return False
        if self.active_to and today > self.active_to:
            return False
        return True
