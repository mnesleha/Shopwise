from django.db import models
from django.core.exceptions import ValidationError

from utils.sanitize import sanitize_markdown
from versatileimagefield.fields import PPOIField, VersatileImageField


CURRENCY_CHOICES = [
    ("EUR", "Euro"),
    ("USD", "US Dollar"),
    ("GBP", "British Pound"),
    ("PLN", "Polish Zloty"),
]


class TaxClass(models.Model):
    """Represents a tax classification that can be assigned to products.

    TaxClass acts as a stable, named category for grouping products by their
    tax treatment (e.g. standard rate, reduced rate, zero rate).  Actual
    rate values are intentionally excluded from this model; they will be
    added in a later pricing phase.
    """

    name = models.CharField(max_length=128)
    code = models.CharField(
        max_length=64,
        unique=True,
        help_text="Stable machine-readable identifier, e.g. 'standard', 'reduced', 'zero'.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional notes visible only in the admin.",
    )
    # Tax rate expressed as a percentage, e.g. 23 means 23 % VAT.
    # Null means "no rate configured" — the pricing service treats this as 0 %.
    # This field stores the canonical rate for the class; multi-country rate
    # tables will be introduced in a later phase.
    rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Tax rate as a percentage (e.g. 23 for 23 %). Leave blank for 0 %.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tax Class"
        verbose_name_plural = "Tax Classes"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)

    # ------------------------------------------------------------------
    # Legacy pricing field — kept for backward compatibility during the
    # transition to the new pricing model.  Do NOT remove until all
    # dependent code has been migrated to price_net_amount.
    # ------------------------------------------------------------------
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # ------------------------------------------------------------------
    # Pricing foundation (Phase 1)
    # Both fields are nullable so the migration is non-destructive.  They
    # will become required once the transition from `price` is complete.
    # ------------------------------------------------------------------
    price_net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Net (pre-tax) price of the product.",
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="EUR",
        help_text="ISO 4217 currency code.",
    )
    tax_class = models.ForeignKey(
        TaxClass,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
        help_text="Tax classification applied to this product.",
    )

    stock_quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey("categories.Category", null=True, blank=True, on_delete=models.SET_NULL, related_name="products")

    # Plain-text teaser shown in catalogue cards and the detail header.
    short_description = models.TextField(blank=True, default="")

    # Full product description in Markdown, rendered on the detail page.
    full_description = models.TextField(blank=True, default="")

    # Designated hero image shown in catalogue cards and detail header.
    # Must belong to this product. Automatically nulled when the referenced
    # ProductImage is deleted (on_delete=SET_NULL).
    primary_image = models.ForeignKey(
        "products.ProductImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    def clean(self):
        errors = {}

        # Name validation
        if not self.name:
            errors["name"] = "Product name cannot be empty"

        # Price validation
        if self.price is not None and self.price <= 0:
            errors["price"] = "Product price must be greater than zero"

        # Stock validation
        if self.stock_quantity is not None and self.stock_quantity < 0:
            errors["stock_quantity"] = "Stock quantity cannot be negative"

        # Ownership: primary_image must belong to this product.
        # Only validated for persisted products (pk exists) because a new
        # product cannot have a primary_image set on first save.
        if self.pk and self.primary_image_id is not None:
            if self.primary_image.product_id != self.pk:
                errors["primary_image"] = "Primary image must belong to this product."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Strip raw HTML from the Markdown description before persisting.
        # Applies to all entry points: admin, API, management commands.
        self.full_description = sanitize_markdown(self.full_description)
        super().save(*args, **kwargs)

    def is_sellable(self) -> bool:
        return self.is_active and self.stock_quantity > 0

    def __str__(self):
        return self.name


def _product_gallery_upload_to(instance: "ProductImage", filename: str) -> str:
    """Return the upload path for a ProductImage file.

    Originals are stored under ``products/gallery/<product_id>/<filename>``.
    VersatileImageField sized renditions will mirror this structure
    automatically under ``__sized__/products/gallery/<product_id>/...``.

    Falls back to ``products/gallery/unsorted/<filename>`` when the instance
    has no ``product_id`` yet (e.g. during an unsaved pre-save upload), though
    this should not occur in normal admin / API workflows.
    """
    product_id = instance.product_id or "unsorted"
    return f"products/gallery/{product_id}/{filename}"


class ProductImage(models.Model):
    """A single catalogue image belonging to a Product.

    Gallery ordering is determined by ``sort_order`` (ascending), with ``id``
    as the tie-breaker.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    # ppoi_field wires the PPOI click widget: when rendered in the admin the
    # image field uses SizedImageCenterpointClickDjangoAdminField, which shows
    # a clickable preview thumbnail and stores the focal-point value in a
    # hidden input.  pre_save() then syncs the chosen point back to `ppoi`.
    image = VersatileImageField(upload_to=_product_gallery_upload_to, ppoi_field="ppoi")
    ppoi = PPOIField()
    alt_text = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"ProductImage(product_id={self.product_id}, sort_order={self.sort_order})"
