from django.contrib import admin
from .models import (
    Discount,
    Offer,
    OrderPromotion,
    Promotion,
    PromotionCategory,
    PromotionProduct,
)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "discount_type",
        "value",
        "is_active",
        "valid_from",
        "valid_to",
        "product",
        "category",
    )
    list_filter = ("discount_type", "is_active")
    search_fields = ("name",)


# ---------------------------------------------------------------------------
# Phase 2 — Promotion admin
# ---------------------------------------------------------------------------


class PromotionProductInline(admin.TabularInline):
    """Inline for managing product targets directly on the Promotion page."""

    model = PromotionProduct
    extra = 1
    autocomplete_fields = ["product"]


class PromotionCategoryInline(admin.TabularInline):
    """Inline for managing category targets directly on the Promotion page."""

    model = PromotionCategory
    extra = 1


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "type",
        "amount_scope",
        "value",
        "priority",
        "is_active",
        "active_from",
        "active_to",
    )
    list_filter = ("type", "amount_scope", "is_active")
    search_fields = ("name", "code")
    ordering = ("-priority", "name")
    inlines = [PromotionProductInline, PromotionCategoryInline]
    fieldsets = (
        (
            None,
            {
                "fields": ("name", "code", "type", "value", "amount_scope", "priority"),
                "description": (
                    "For FIXED promotions, <em>Amount scope</em> controls whether the fixed "
                    "amount is deducted from the gross (customer-visible) price or the net "
                    "(pre-tax) price. Defaults to Gross (B2C-friendly)."
                ),
            },
        ),
        (
            "Scheduling",
            {
                "fields": ("is_active", "active_from", "active_to"),
                "description": "Leave date fields blank to make the promotion always valid.",
            },
        ),
        (
            "Notes",
            {
                "fields": ("description",),
                "classes": ("collapse",),
            },
        ),
    )


# ---------------------------------------------------------------------------
# Phase 4 / Slice 1 — Order-level promotion admin
# ---------------------------------------------------------------------------


class OfferInline(admin.TabularInline):
    """Inline for viewing/creating offers linked to an OrderPromotion."""

    model = Offer
    extra = 0
    fields = ("token", "status", "is_active", "active_from", "active_to")
    readonly_fields = ()


@admin.register(OrderPromotion)
class OrderPromotionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "type",
        "value",
        "acquisition_mode",
        "stacking_policy",
        "priority",
        "is_active",
        "is_discoverable",
        "minimum_order_value",
        "active_from",
        "active_to",
    )
    list_filter = ("type", "acquisition_mode", "stacking_policy", "is_active", "is_discoverable")
    search_fields = ("name", "code")
    ordering = ("-priority", "name")
    inlines = [OfferInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "code",
                    "type",
                    "value",
                    "acquisition_mode",
                    "stacking_policy",
                    "priority",
                    "minimum_order_value",
                ),
            },
        ),
        (
            "Scheduling",
            {
                "fields": ("is_active", "active_from", "active_to", "is_discoverable"),
                "description": "Leave date fields blank to make the promotion always valid.",
            },
        ),
        (
            "Notes",
            {
                "fields": ("description",),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "token",
        "promotion",
        "status",
        "is_active",
        "active_from",
        "active_to",
    )
    list_filter = ("status", "is_active")
    search_fields = ("token", "promotion__code", "promotion__name")
    ordering = ("token",)
    raw_id_fields = ("promotion",)
