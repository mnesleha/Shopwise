from django.contrib import admin
from django.conf import settings
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.contrib import messages
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe

from notifications.jobs import send_campaign_offer_email as _send_campaign_offer_email
from .forms import CampaignCreateForm
from .services.campaign import create_and_send_campaign_offer
from .models import (
    AcquisitionMode,
    Discount,
    Offer,
    OfferStatus,
    OrderPromotion,
    Promotion,
    PromotionCategory,
    PromotionProduct,
    PromotionType,
    StackingPolicy,
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
# Phase 4 — Order-level promotion admin
# ---------------------------------------------------------------------------

# Human-readable explanations for each acquisition mode.
_ACQUISITION_MODE_HELP: dict[str, str] = {
    AcquisitionMode.AUTO_APPLY: (
        "The platform applies this discount automatically — no action required from the customer. "
        "Use this for always-on promotions and threshold rewards."
    ),
    AcquisitionMode.CAMPAIGN_APPLY: (
        "This discount is delivered via a tokenized campaign link (e.g. an email offer). "
        "The customer must follow the link or enter the token to activate it. "
        "Create an Offer record below to generate a distributable token."
    ),
    AcquisitionMode.MANUAL_ENTRY: (
        "The customer must manually enter a coupon code at checkout. "
        "This is a fallback mechanism — prefer Campaign apply for distributed offers."
    ),
}

# Human-readable explanations for stacking policy choices.
_STACKING_POLICY_HELP: dict[str, str] = {
    StackingPolicy.EXCLUSIVE: (
        "Only one order-level discount is applied per order — the one that gives the "
        "customer the largest saving. This promotion will not combine with other order-level discounts."
    ),
    StackingPolicy.STACKABLE_WITH_LINE: (
        "This discount can coexist alongside line-level (product) promotions. "
        "However, it still does not combine with other order-level discounts."
    ),
}


def _format_value(obj: "OrderPromotion") -> str:
    """Return a human-readable value string, e.g. '10%' or '€50.00'."""
    if obj.type == PromotionType.PERCENT:
        # Normalize the Decimal to strip insignificant trailing zeros
        # (e.g. Decimal("15.00") → "15"), then append the percent sign.
        return f"{obj.value.normalize():f}%"
    return f"€{obj.value:.2f}"


class OfferInline(admin.TabularInline):
    """Inline for viewing/creating campaign offer tokens linked to this promotion."""

    model = Offer
    extra = 0
    fields = ("token", "status", "is_active", "active_from", "active_to")
    readonly_fields = ("status",)
    verbose_name = "Campaign offer token"
    verbose_name_plural = "Campaign offer tokens"
    show_change_link = True


@admin.register(OrderPromotion)
class OrderPromotionAdmin(admin.ModelAdmin):
    # ── List view ────────────────────────────────────────────────────────────

    change_list_template = "admin/discounts/orderpromotion/change_list.html"

    list_display = (
        "name",
        "discount_display",
        "acquisition_mode",
        "threshold_display",
        "is_active",
        "is_discoverable",
        "active_from",
        "active_to",
    )
    list_display_links = ("name",)
    list_filter = (
        "acquisition_mode",
        "type",
        "stacking_policy",
        "is_active",
        "is_discoverable",
    )
    search_fields = ("name", "code")
    ordering = ("-is_active", "-priority", "name")
    inlines = [OfferInline]

    # ── Computed list columns ────────────────────────────────────────────────

    @admin.display(description="Discount")
    def discount_display(self, obj: "OrderPromotion") -> str:
        """Return a concise discount summary, e.g. 'FIXED €50.00'."""
        return f"{obj.get_type_display()} {_format_value(obj)}"

    @admin.display(description="Min. order", boolean=False)
    def threshold_display(self, obj: "OrderPromotion") -> str:
        """Return minimum order value or '—' when there is no threshold."""
        if obj.minimum_order_value is not None:
            return f"€{obj.minimum_order_value:.2f}"
        return "—"

    # ── Form help text (injected per-request so they can reference live data) ─

    def get_form(self, request, obj=None, **kwargs):
        """Attach merchant-readable field help texts."""
        kwargs.setdefault("help_texts", {})
        kwargs["help_texts"].update(
            {
                "name": (
                    "Customer-visible promotion name shown in cart and order confirmation messages. "
                    "Keep it short and benefit-focused, e.g. 'Summer 10% Order Discount'."
                ),
                "code": (
                    "Internal identifier used for logging and campaign linking. "
                    "Use lowercase-with-hyphens, e.g. <code>summer-2026-order-10pct</code>. "
                    "Cannot be changed after offers are linked to this promotion."
                ),
                "type": (
                    "<strong>PERCENT</strong> — applies a percentage reduction to the cart total "
                    "(e.g. value = 10 means 10% off). "
                    "<strong>FIXED</strong> — deducts a fixed amount from the cart total "
                    "(e.g. value = 50 means €50 off)."
                ),
                "value": (
                    "The discount magnitude. "
                    "For PERCENT: enter a number between 1 and 100 (e.g. <code>10</code> for 10%). "
                    "For FIXED: enter the amount in the store currency (e.g. <code>50</code> for €50)."
                ),
                "acquisition_mode": (
                    "<strong>Auto-apply</strong>: platform automatically applies the discount when "
                    "the cart qualifies — no customer action needed. "
                    "<strong>Campaign apply</strong>: activated via a tokenized offer link (email / "
                    "landing page). Create an Offer token below. "
                    "<strong>Manual entry</strong>: customer types a code at checkout (fallback only)."
                ),
                "minimum_order_value": (
                    "Optional. When set, this promotion only activates once the cart gross total "
                    "reaches this value <em>after</em> line-level discounts are applied. "
                    "Leave blank for a discount with no minimum spend."
                ),
                "stacking_policy": (
                    "<strong>Exclusive</strong>: only the single best order-level discount is "
                    "applied per order. This promotion will not combine with other order-level "
                    "discounts, but may coexist with line-level (product) promotions. "
                    "<strong>Stackable with line-level</strong>: same exclusivity rule as above, "
                    "but explicitly documents that line-level promotions are untouched."
                ),
                "is_discoverable": (
                    "When enabled, this promotion can be surfaced to customers in storefront "
                    "messaging (e.g. 'Spend €X more to unlock this offer'). "
                    "Disable to keep the promotion silent — it will still be applied, but the "
                    "customer will not be nudged toward it."
                ),
                "priority": (
                    "<strong>Advanced tiebreak field — most merchants can leave this at 0.</strong> "
                    "The storefront always applies the order-level discount that gives the customer "
                    "the largest gross saving. Priority is only consulted when two eligible "
                    "promotions produce exactly equal customer benefit — the one with the higher "
                    "priority value wins. It does <em>not</em> override a promotion that saves the "
                    "customer more money."
                ),
                "description": (
                    "Internal notes for your team. Not shown to customers."
                ),
            }
        )
        return super().get_form(request, obj, **kwargs)

    # ── Readonly summary field ───────────────────────────────────────────────

    def promotion_summary(self, obj: "OrderPromotion") -> str:  # pragma: no cover
        """Contextual summary rendered at the top of an existing promotion's form."""
        if obj.pk is None:
            return ""

        mode_text = _ACQUISITION_MODE_HELP.get(obj.acquisition_mode, "")
        threshold_text = ""
        if obj.minimum_order_value is not None:
            threshold_text = (
                f" The discount activates once the cart reaches "
                f"<strong>€{obj.minimum_order_value:.2f}</strong>."
            )
        discover_text = (
            " Storefront messaging <strong>will</strong> surface this promotion to customers."
            if obj.is_discoverable
            else " Storefront messaging will <strong>not</strong> nudge customers toward this promotion."
        )
        return format_html(
            "<p style='margin:0 0 4px'><strong>{name}</strong> — "
            "{type_label} of <strong>{value}</strong>.</p>"
            "<p style='margin:0 0 4px'>{mode_text}{threshold_text}{discover_text}</p>",
            name=obj.name,
            type_label=obj.get_type_display(),
            value=_format_value(obj),
            mode_text=mark_safe(mode_text),
            threshold_text=mark_safe(threshold_text),
            discover_text=mark_safe(discover_text),
        )

    promotion_summary.short_description = "Summary"  # type: ignore[attr-defined]
    promotion_summary.allow_tags = True  # type: ignore[attr-defined]

    # ── Fieldsets ────────────────────────────────────────────────────────────

    readonly_fields = ("promotion_summary",)

    fieldsets = (
        (
            "Promotion basics",
            {
                "fields": ("promotion_summary", "name", "code"),
                "description": (
                    "The <em>Name</em> is shown to the customer in the cart and order "
                    "confirmation. The <em>Code</em> is an internal identifier — it cannot "
                    "be changed once offer tokens have been issued."
                ),
            },
        ),
        (
            "Discount",
            {
                "fields": ("type", "value"),
                "description": (
                    "Choose the discount type and enter its magnitude. "
                    "The storefront applies the order-level discount after line-level "
                    "(product) promotions, on the post-line-discount cart total."
                ),
            },
        ),
        (
            "How the customer receives it",
            {
                "fields": ("acquisition_mode",),
                "description": (
                    "<strong>Auto-apply</strong>: applied automatically once the cart qualifies. "
                    "No customer action needed. "
                    "Optionally set a <em>Minimum order value</em> below to make it a "
                    "threshold reward. "
                    "<br>"
                    "<strong>Campaign apply</strong>: activated via a tokenized offer link. "
                    "Add an Offer token in the section at the bottom of this page. "
                    "<br>"
                    "<strong>Manual entry</strong>: customer types a code at checkout (fallback only)."
                ),
            },
        ),
        (
            "Qualification / minimum order",
            {
                "fields": ("minimum_order_value",),
                "description": (
                    "Leave blank for no minimum spend. "
                    "When set, the promotion only activates after the cart gross total "
                    "(after any line-level discounts) reaches this value. "
                    "The storefront can show customers how much more they need to spend to "
                    "unlock this offer — set <em>Customer visibility</em> below accordingly."
                ),
            },
        ),
        (
            "Exclusivity",
            {
                "fields": ("stacking_policy",),
                "description": (
                    "Order-level promotions do not stack with each other — "
                    "the storefront selects exactly one winner per order. "
                    "The winner is the eligible promotion that gives the customer "
                    "the <strong>largest gross saving</strong>."
                ),
            },
        ),
        (
            "Customer visibility",
            {
                "fields": ("is_discoverable",),
                "description": (
                    "Controls whether this promotion appears in storefront messaging "
                    "(e.g. progress banners, unlock nudges). "
                    "The promotion is applied regardless of this setting."
                ),
            },
        ),
        (
            "Advanced — Priority",
            {
                "fields": ("priority",),
                "classes": ("collapse",),
                "description": (
                    "<strong>Most merchants do not need to change this.</strong> "
                    "The storefront winner is always the promotion with the highest customer "
                    "benefit. Priority is only used to break ties when two promotions produce "
                    "exactly equal gross savings — the higher priority value wins. "
                    "Priority does <em>not</em> override a promotion that saves the customer more."
                ),
            },
        ),
        (
            "Scheduling",
            {
                "fields": ("is_active", "active_from", "active_to"),
                "description": (
                    "Use <em>Active</em> as a master on/off switch. "
                    "Set optional date bounds to restrict eligibility to a time window. "
                    "Leave both dates blank for an always-valid promotion."
                ),
            },
        ),
        (
            "Internal notes",
            {
                "fields": ("description",),
                "classes": ("collapse",),
                "description": "Optional notes for your team. Not shown to customers.",
            },
        ),
    )

    # ── Custom URL: guided campaign creation flow ────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "campaign/new/",
                self.admin_site.admin_view(self.campaign_create_view),
                name="discounts_orderpromotion_campaign_new",
            ),
        ]
        return custom + urls

    def campaign_create_view(self, request):
        """Guided one-page flow: define a CAMPAIGN_APPLY promotion and send the claim link.

        GET  — render the blank campaign creation form.
        POST — validate, create OrderPromotion + Offer, send email, redirect on success.
        """
        if request.method == "POST":
            form = CampaignCreateForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                try:
                    promotion, offer, claim_url = create_and_send_campaign_offer(
                        name=cd["name"],
                        code=cd["code"],
                        type=cd["type"],
                        value=cd["value"],
                        recipient_email=cd["recipient_email"],
                        minimum_order_value=cd.get("minimum_order_value"),
                        is_discoverable=cd.get("is_discoverable", False),
                        active_from=cd.get("active_from"),
                        active_to=cd.get("active_to"),
                        offer_active_to=cd.get("offer_active_to"),
                    )
                except Exception as exc:
                    self.message_user(
                        request,
                        f"Campaign creation failed: {exc}",
                        level=messages.ERROR,
                    )
                    # Re-render the form with the submitted values intact.
                    context = self._campaign_view_context(request, form, claim_url=None)
                    return TemplateResponse(
                        request,
                        "admin/discounts/campaign_create.html",
                        context,
                    )

                self.message_user(
                    request,
                    format_html(
                        'Campaign <strong>{name}</strong> created. '
                        'Offer token <code>{token}</code> generated. '
                        'Claim email sent to <strong>{email}</strong>.',
                        name=promotion.name,
                        token=offer.token,
                        email=cd["recipient_email"],
                    ),
                    level=messages.SUCCESS,
                )
                change_url = reverse(
                    "admin:discounts_orderpromotion_change",
                    args=[promotion.pk],
                )
                return HttpResponseRedirect(change_url)
        else:
            form = CampaignCreateForm()

        context = self._campaign_view_context(request, form, claim_url=None)
        return TemplateResponse(
            request,
            "admin/discounts/campaign_create.html",
            context,
        )

    def _campaign_view_context(self, request, form, claim_url):
        """Build the template context dict for the campaign creation view."""
        return {
            **self.admin_site.each_context(request),
            "form": form,
            "claim_url": claim_url,
            "opts": self.model._meta,
            "title": "Create and send campaign",
        }


# ---------------------------------------------------------------------------
# Offer admin
# ---------------------------------------------------------------------------


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    # ── List view ────────────────────────────────────────────────────────────

    list_display = (
        "token",
        "promotion_link",
        "promotion_discount_display",
        "status",
        "is_active",
        "active_from",
        "active_to",
    )
    list_display_links = ("token",)
    list_filter = ("status", "is_active", "promotion__acquisition_mode")
    search_fields = ("token", "promotion__code", "promotion__name")
    ordering = ("-is_active", "status", "token")
    raw_id_fields = ("promotion",)
    actions = ["send_offer_email"]

    # ── Computed list columns ────────────────────────────────────────────────

    @admin.display(description="Linked promotion")
    def promotion_link(self, obj: "Offer") -> str:
        """Return the linked promotion name and code for quick scanning."""
        return f"{obj.promotion.name} ({obj.promotion.code})"

    @admin.display(description="Promotion discount")
    def promotion_discount_display(self, obj: "Offer") -> str:
        """Return a compact discount summary for the linked promotion."""
        return f"{obj.promotion.get_type_display()} {_format_value(obj.promotion)}"

    # ── Readonly summary field ───────────────────────────────────────────────

    def offer_summary(self, obj: "Offer") -> str:  # pragma: no cover
        """Explain what this offer token does and how it is used."""
        if obj.pk is None:
            return ""

        mode = obj.promotion.acquisition_mode
        if mode == AcquisitionMode.CAMPAIGN_APPLY:
            delivery_text = (
                "This is a <strong>campaign offer</strong>. "
                "The customer receives it via a tokenized link (e.g. an email). "
                "When they follow the link, the discount is activated on their cart."
            )
        elif mode == AcquisitionMode.MANUAL_ENTRY:
            delivery_text = (
                "This is a <strong>manual-entry coupon</strong>. "
                "The customer types the token at checkout to activate the discount."
            )
        else:
            delivery_text = (
                "This offer is linked to an Auto-apply promotion. "
                "The promotion is applied automatically; this token is for record-keeping."
            )

        status_label = obj.get_status_display()
        return format_html(
            "<p style='margin:0 0 4px'>{delivery_text}</p>"
            "<p style='margin:0 0 4px'>Current status: <strong>{status}</strong>. "
            "The token is <strong>{active}</strong>.</p>",
            delivery_text=mark_safe(delivery_text),
            status=status_label,
            active="active" if obj.is_active else "inactive",
        )

    offer_summary.short_description = "How this offer works"  # type: ignore[attr-defined]
    offer_summary.allow_tags = True  # type: ignore[attr-defined]

    # ── Form help text ───────────────────────────────────────────────────────

    def get_form(self, request, obj=None, **kwargs):
        """Attach merchant-readable field help texts for the Offer form."""
        kwargs.setdefault("help_texts", {})
        kwargs["help_texts"].update(
            {
                "token": (
                    "The unique code or identifier for this offer. "
                    "For <strong>Campaign apply</strong> promotions this is embedded in the "
                    "offer URL sent to the customer. "
                    "For <strong>Manual entry</strong> promotions this is what the customer "
                    "types at checkout. "
                    "Use a UUID or a human-readable slug — must be globally unique."
                ),
                "promotion": (
                    "The order-level promotion this offer unlocks. "
                    "Only <strong>Campaign apply</strong> and <strong>Manual entry</strong> "
                    "promotions should have offer tokens."
                ),
                "status": (
                    "Lifecycle stage of this offer token. "
                    "<strong>Created</strong>: generated but not yet sent. "
                    "<strong>Delivered</strong>: sent to the customer. "
                    "<strong>Claimed</strong>: customer has activated it. "
                    "<strong>Redeemed</strong>: successfully applied at checkout. "
                    "<strong>Expired</strong>: invalidated or past its validity window."
                ),
                "is_active": (
                    "Master on/off switch. Inactive offers cannot be claimed regardless of status. "
                    "Deactivate an offer to revoke it without deleting the record."
                ),
                "active_from": (
                    "Optional start date from which the offer can be claimed. "
                    "Leave blank for no lower bound."
                ),
                "active_to": (
                    "Optional expiry date after which the offer can no longer be claimed. "
                    "Leave blank for no expiry."
                ),
                "description": (
                    "Internal notes — not shown to customers. "
                    "Useful for recording distribution context (e.g. 'Sent to newsletter segment Q1-2026')."
                ),
            }
        )
        return super().get_form(request, obj, **kwargs)

    # ── Fieldsets ────────────────────────────────────────────────────────────

    readonly_fields = ("offer_summary", "status")

    fieldsets = (
        (
            "Offer token",
            {
                "fields": ("offer_summary", "token", "promotion"),
                "description": (
                    "An Offer token is a distributable instance of an order-level promotion. "
                    "The customer uses the token (via a link or by typing it at checkout) to "
                    "activate the linked promotion on their cart."
                ),
            },
        ),
        (
            "Status",
            {
                "fields": ("status", "is_active"),
                "description": (
                    "Track the offer through its lifecycle. "
                    "Use <em>Active</em> as a hard on/off switch — "
                    "deactivating an offer revokes it immediately."
                ),
            },
        ),
        (
            "Validity window",
            {
                "fields": ("active_from", "active_to"),
                "description": "Leave both blank for an always-valid offer.",
            },
        ),
        (
            "Internal notes",
            {
                "fields": ("description",),
                "classes": ("collapse",),
            },
        ),
    )

    # ── Admin action: send offer email ────────────────────────────────────────

    @admin.action(description="Send campaign offer email to a recipient")
    def send_offer_email(self, request, queryset):
        """Admin action: send a campaign-applied offer via email to a chosen recipient.

        Phase 4 / Slice 5A.
        Supports a single offer at a time.  The promotion must be CAMPAIGN_APPLY.
        """
        if queryset.count() != 1:
            self.message_user(
                request,
                "Please select exactly one offer to send.",
                level=messages.ERROR,
            )
            return

        offer = queryset.first()

        if offer.promotion.acquisition_mode != AcquisitionMode.CAMPAIGN_APPLY:
            self.message_user(
                request,
                (
                    f"Offer '{offer.token}' cannot be sent: its linked promotion "
                    f"({offer.promotion.code}) is not a Campaign apply promotion."
                ),
                level=messages.ERROR,
            )
            return

        # Step 2: form submitted with the recipient email address.
        if "confirm" in request.POST:
            recipient_email = request.POST.get("recipient_email", "").strip()
            if not recipient_email:
                self.message_user(
                    request,
                    "Recipient email is required.",
                    level=messages.ERROR,
                )
                return

            offer_url = (
                f"{settings.PUBLIC_BASE_URL}/claim-offer?token={offer.token}"
            )
            sent = _send_campaign_offer_email(
                recipient_email=recipient_email,
                offer_url=offer_url,
                promotion_name=offer.promotion.name,
            )
            if sent:
                # Advance lifecycle: CREATED / DELIVERED → DELIVERED.
                # Do not overwrite CLAIMED or REDEEMED.
                Offer.objects.filter(
                    pk=offer.pk,
                    status__in=[OfferStatus.CREATED, OfferStatus.DELIVERED],
                ).update(status=OfferStatus.DELIVERED)
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
