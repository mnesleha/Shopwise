from django.conf import settings
from rest_framework import serializers
from versatileimagefield.serializers import VersatileImageFieldSerializer

from products.models import Product, ProductImage
from products.services.pricing import get_product_pricing

# ---------------------------------------------------------------------------
# Pricing serializers — nested Phase 2 structure
# ---------------------------------------------------------------------------


class _PricingTierSerializer(serializers.Serializer):
    """Serialises a single ``PricingTierResult`` (undiscounted or discounted).

    Amounts are decimal strings; currency is ISO 4217; tax_rate is a
    percentage string with trailing zeros stripped (e.g. ``"23"`` not
    ``"23.0000"``).
    """

    net = serializers.SerializerMethodField(help_text="Net (pre-tax) price.")
    gross = serializers.SerializerMethodField(help_text="Gross (post-tax) price.")
    tax = serializers.SerializerMethodField(help_text="Tax component (gross − net).")
    currency = serializers.SerializerMethodField(help_text="ISO 4217 currency code.")
    tax_rate = serializers.SerializerMethodField(
        help_text="Applied tax rate as a percentage, e.g. '23' for 23 %."
    )

    def get_net(self, obj) -> str:
        return str(obj.net.amount)

    def get_gross(self, obj) -> str:
        return str(obj.gross.amount)

    def get_tax(self, obj) -> str:
        return str(obj.tax.amount)

    def get_currency(self, obj) -> str:
        return obj.currency

    def get_tax_rate(self, obj) -> str:
        return format(obj.tax_rate.normalize(), "f")


class _DiscountResultSerializer(serializers.Serializer):
    """Serialises a ``DiscountResult``.

    All monetary amounts are decimal strings.  ``percentage``,
    ``promotion_code``, and ``promotion_type`` may be ``null`` when no
    promotion was applied or when a percentage cannot be computed.
    """

    amount_net = serializers.SerializerMethodField(
        help_text="Discount deducted from the net price."
    )
    amount_gross = serializers.SerializerMethodField(
        help_text="Gross-equivalent of the discount (undiscounted_gross − discounted_gross)."
    )
    percentage = serializers.SerializerMethodField(
        help_text="Effective percentage discount relative to the undiscounted net price, or null."
    )
    promotion_code = serializers.SerializerMethodField(
        help_text="Stable code of the winning promotion, or null."
    )
    promotion_type = serializers.SerializerMethodField(
        help_text="'PERCENT' or 'FIXED', or null when no promotion applies."
    )

    def get_amount_net(self, obj) -> str:
        return str(obj.amount_net.amount)

    def get_amount_gross(self, obj) -> str:
        return str(obj.amount_gross.amount)

    def get_percentage(self, obj):
        if obj.percentage is None:
            return None
        return str(obj.percentage)

    def get_promotion_code(self, obj):
        return obj.promotion_code

    def get_promotion_type(self, obj):
        return obj.promotion_type


class ProductPricingResultSerializer(serializers.Serializer):
    """Full promotion-aware pricing breakdown for a product.

    Structure::

        {
          "undiscounted": { "net": "...", "gross": "...", "tax": "...",
                            "currency": "...", "tax_rate": "..." },
          "discounted":   { "net": "...", "gross": "...", "tax": "...",
                            "currency": "...", "tax_rate": "..." },
          "discount": {
            "amount_net": "...",
            "amount_gross": "...",
            "percentage": "...",   // null when no promotion
            "promotion_code": ..., // null when no promotion
            "promotion_type": ...  // null when no promotion
          }
        }

    When no promotion applies, ``undiscounted`` == ``discounted`` and all
    ``discount.*`` amounts are ``"0.00"`` (percentage is ``"0"``).
    """

    undiscounted = serializers.SerializerMethodField(
        help_text="Full pricing without any promotion applied."
    )
    discounted = serializers.SerializerMethodField(
        help_text="Pricing after the winning line promotion (equal to undiscounted when none applies)."
    )
    discount = serializers.SerializerMethodField(
        help_text="Breakdown of the applied discount; amounts are 0.00 when no promotion applies."
    )

    def get_undiscounted(self, obj):
        return _PricingTierSerializer(obj.undiscounted).data

    def get_discounted(self, obj):
        return _PricingTierSerializer(obj.discounted).data

    def get_discount(self, obj):
        return _DiscountResultSerializer(obj.discount).data


# ---------------------------------------------------------------------------
# Stock status constants
# ---------------------------------------------------------------------------

IN_STOCK = "IN_STOCK"
LOW_STOCK = "LOW_STOCK"
OUT_OF_STOCK = "OUT_OF_STOCK"

_STOCK_STATUS_CHOICES = [IN_STOCK, LOW_STOCK, OUT_OF_STOCK]

# VersatileImageField size keys used for all image payloads.
# FE consumers must use these URLs directly — never construct media paths.
_IMAGE_SIZES = [
    ("thumb", "thumbnail__100x100"),
    ("medium", "thumbnail__400x400"),
    ("large", "thumbnail__800x800"),
    ("full", "url"),
]


def _compute_stock_status(stock_quantity: int) -> str:
    threshold: int = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
    if stock_quantity <= 0:
        return OUT_OF_STOCK
    if stock_quantity <= threshold:
        return LOW_STOCK
    return IN_STOCK


# ---------------------------------------------------------------------------
# Image serializers
# ---------------------------------------------------------------------------


class ProductImageSerializer(serializers.ModelSerializer):
    """Serialises a ProductImage with ready-to-use URL variants.

    All URL variants are absolute when a ``request`` is present in context.
    FE must not construct media URLs — consume ``thumb``, ``medium``,
    ``large``, or ``full`` directly.
    """

    image = VersatileImageFieldSerializer(sizes=_IMAGE_SIZES)

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "sort_order"]


# ---------------------------------------------------------------------------
# Product serializers
# ---------------------------------------------------------------------------


class ProductSerializer(serializers.ModelSerializer):
    """Catalogue / list serializer — omits full_description to keep response compact."""

    stock_status = serializers.SerializerMethodField(
        help_text="IN_STOCK | LOW_STOCK | OUT_OF_STOCK"
    )
    primary_image = serializers.SerializerMethodField(
        help_text="Hero image URL variants, or null if none is set."
    )
    pricing = serializers.SerializerMethodField(
        help_text="Structured pricing breakdown (net/gross/tax). Null when price_net_amount is not set."
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category_id",
            "price",
            "pricing",
            "stock_quantity",
            "stock_status",
            "short_description",
            "primary_image",
        ]

    def get_stock_status(self, obj: Product) -> str:
        return _compute_stock_status(obj.stock_quantity)

    def get_primary_image(self, obj: Product):
        if obj.primary_image_id is None:
            return None
        return ProductImageSerializer(
            obj.primary_image, context=self.context
        ).data

    def get_pricing(self, obj: Product):
        result = get_product_pricing(obj)
        if result is None:
            return None
        return ProductPricingResultSerializer(result).data


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detail serializer — includes both description fields and full gallery."""

    stock_status = serializers.SerializerMethodField(
        help_text="IN_STOCK | LOW_STOCK | OUT_OF_STOCK"
    )
    primary_image = serializers.SerializerMethodField(
        help_text="Hero image URL variants, or null if none is set."
    )
    gallery_images = serializers.SerializerMethodField(
        help_text="All gallery images ordered by sort_order, id."
    )
    pricing = serializers.SerializerMethodField(
        help_text="Structured pricing breakdown (net/gross/tax). Null when price_net_amount is not set."
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category_id",
            "price",
            "pricing",
            "stock_quantity",
            "stock_status",
            "short_description",
            "full_description",
            "primary_image",
            "gallery_images",
        ]

    def get_stock_status(self, obj: Product) -> str:
        return _compute_stock_status(obj.stock_quantity)

    def get_primary_image(self, obj: Product):
        if obj.primary_image_id is None:
            return None
        return ProductImageSerializer(
            obj.primary_image, context=self.context
        ).data

    def get_gallery_images(self, obj: Product):
        images = obj.images.all()
        return ProductImageSerializer(images, many=True, context=self.context).data

    def get_pricing(self, obj: Product):
        result = get_product_pricing(obj)
        if result is None:
            return None
        return ProductPricingResultSerializer(result).data