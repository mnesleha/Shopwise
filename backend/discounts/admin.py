from django.contrib import admin
from django.conf import settings
from django.template.response import TemplateResponse

from notifications.jobs import send_campaign_offer_email as _send_campaign_offer_email
from .models import (
    AcquisitionMode,
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

    def get_form(self, request, obj=None, **kwargs):
        """Attach field-level help text so merchants see inline guidance."""
        kwargs.setdefault("help_texts", {})
        kwargs["help_texts"].update(
            {
                "priority": (
                    "Higher value wins. When two exclusive order discounts are eligible at the "
                    "same time, the one with the <strong>highest priority</strong> is applied — "
                    "regardless of which one would give a larger discount. "
                    "Use equal priorities when you want the larger discount to win instead."
                ),
                "stacking_policy": (
                    "<strong>EXCLUSIVE</strong> promotions do not combine with other "
                    "order-level promotions — only the single winner is applied."
                ),
            }
        )
        return super().get_form(request, obj, **kwargs)

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
                "description": (
                    "<strong>Winner resolution for simultaneous exclusive promotions:</strong> "
                    "highest priority wins first; if equal, the larger customer discount wins; "
                    "if still equal, the lower ID wins. Only one order-level promotion is "
                    "ever applied at a time."
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
    actions = ["send_offer_email"]

    @admin.action(description="Send campaign offer email")
    def send_offer_email(self, request, queryset):
        """Admin action: send a campaign-applied offer via email to a chosen recipient.

        Phase 4 / Slice 5A.
        Supports a single offer at a time.  The promotion must be CAMPAIGN_APPLY.
        """
        if queryset.count() != 1:
            self.message_user(
                request,
                "Please select exactly one offer to send.",
                level="error",
            )
            return

        offer = queryset.first()

        if offer.promotion.acquisition_mode != AcquisitionMode.CAMPAIGN_APPLY:
            self.message_user(
                request,
                (
                    f"Offer '{offer.token}' cannot be sent: its promotion "
                    f"({offer.promotion.code}) is not CAMPAIGN_APPLY."
                ),
                level="error",
            )
            return

        # Step 2: form submitted with the recipient email address.
        if "confirm" in request.POST:
            recipient_email = request.POST.get("recipient_email", "").strip()
            if not recipient_email:
                self.message_user(
                    request, "Recipient email is required.", level="error"
                )
                return

            offer_url = (
                f"{settings.PUBLIC_BASE_URL}/claim-offer?token={offer.token}"
            )
            _send_campaign_offer_email(
                recipient_email=recipient_email,
                offer_url=offer_url,
                promotion_name=offer.promotion.name,
            )
            self.message_user(
                request,
                f"Campaign offer email sent to {recipient_email}.",
            )
            return

        # Step 1: render intermediate form asking for recipient email.
        return TemplateResponse(
            request,
            "admin/discounts/send_offer_email.html",
            {
                "offer": offer,
                "opts": self.model._meta,
                "title": "Send campaign offer email",
            },
        )
