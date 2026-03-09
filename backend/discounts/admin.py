from django.contrib import admin
from .models import Discount, Promotion, PromotionProduct, PromotionCategory


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
        "value",
        "priority",
        "is_active",
        "active_from",
        "active_to",
    )
    list_filter = ("type", "is_active")
    search_fields = ("name", "code")
    ordering = ("-priority", "name")
    inlines = [PromotionProductInline, PromotionCategoryInline]
    fieldsets = (
        (
            None,
            {
                "fields": ("name", "code", "type", "value", "priority"),
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
