from django.db import models
from django.core.exceptions import ValidationError
from prices import Money, TaxedMoney

from utils.sanitize import sanitize_markdown
from versatileimagefield.fields import PPOIField, VersatileImageField


CURRENCY_CHOICES = [
    ("EUR", "Euro"),
    ("USD", "US Dollar"),
    ("GBP", "British Pound"),
    ("PLN", "Polish Zloty"),
]


class TaxClass(models.Model):
    """Tax classification that can be assigned to products.

    ``TaxClass`` is a stable, named category for grouping products by their
    tax treatment (e.g. standard rate, reduced rate, zero rate).  A flat
    ``rate`` percentage is stored directly on the class for Phase 1; multi-
    country rate tables and external provider support will be introduced in a
    later pricing phase.
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
    slug = models.SlugField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Stable product identifier for seed data, tests, and storefront URLs.",
    )

    # ------------------------------------------------------------------
    # Legacy pricing field (TRANSITIONAL)
    # This field was the sole price representation before Phase 1.  It is
    # kept for backward compatibility while all consumers migrate to
    # price_net_amount + currency + tax_class.
    # DO NOT remove until all call-sites are confirmed migrated.
    # ------------------------------------------------------------------
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # ------------------------------------------------------------------
    # Pricing foundation (Phase 1) — canonical source of truth for pricing
    # Nullable to allow safe non-destructive migration from the legacy field.
    # Once migration is complete these fields will become required.
    # Use products.services.pricing.get_product_pricing() to obtain the
    # full tax breakdown; do NOT compute pricing directly from these fields.
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

    # ------------------------------------------------------------------
    # Derived gross amount — stored so that django-prices TaxedMoneyField
    # can expose a typed TaxedMoney object on the model instance.
    # WARNING: this is NOT a business authority.  It is re-computed by
    # Product.save() from the tax resolver every time the product is saved.
    # Do NOT read this column to make pricing decisions; use
    # get_product_pricing() instead.
    # ------------------------------------------------------------------
    price_gross_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
        help_text=(
            "Gross (post-tax) price — derived from price_net_amount via the tax "
            "resolver on every save.  Read-only; do not set directly."
        ),
    )

    # ------------------------------------------------------------------
    # django-prices typed accessors (plain Python properties)
    # Using @property instead of MoneyField/TaxedMoneyField descriptors
    # avoids those descriptors calling cls._meta.add_field() and landing
    # in opts.fields, which breaks DRF serializer introspection.
    # These provide the same typed Money / TaxedMoney interface.
    # ------------------------------------------------------------------

    @property
    def price_net(self):
        """Net unit price as a prices.Money, or None when unset."""
        if self.price_net_amount is None:
            return None
        return Money(self.price_net_amount, self.currency)

    @price_net.setter
    def price_net(self, value):
        """Assign a Money to write through to price_net_amount and currency."""
        if value is None:
            self.price_net_amount = None
        else:
            self.price_net_amount = value.amount
            self.currency = value.currency

    @property
    def price_gross(self):
        """Gross unit price as a prices.Money, or None when price_gross_amount is unset."""
        if self.price_gross_amount is None:
            return None
        return Money(self.price_gross_amount, self.currency)

    @property
    def taxed_price(self):
        """Combined prices.TaxedMoney, or None when either amount is unset."""
        if self.price_net_amount is None or self.price_gross_amount is None:
            return None
        return TaxedMoney(
            net=Money(self.price_net_amount, self.currency),
            gross=Money(self.price_gross_amount, self.currency),
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
        # Synchronize price_gross_amount from the tax resolver so that the
        # django-prices TaxedMoneyField / price_gross descriptor stay consistent.
        # price_net_amount is canonical; price_gross_amount is always derived.
        if self.price_net_amount is not None:
            # Lazy import to avoid circular dependency (tax_resolver imports TaxClass).
            from products.services.tax_resolver import resolve_tax  # noqa: PLC0415
            taxed = resolve_tax(
                net_amount=self.price_net_amount,
                currency=self.currency,
                tax_class=self.tax_class,
            )
            self.price_gross_amount = taxed.gross.amount
        else:
            self.price_gross_amount = None

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
