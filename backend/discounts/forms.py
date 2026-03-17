"""Forms for the campaign creation guided admin flow.

Phase 4 / Admin Slice 2 — Campaign creation wizard.

These forms are used exclusively by the custom Django admin campaign creation view.
They deliberately do not surface Offer.status or token mechanics to the merchant.
"""

from decimal import Decimal

from django import forms

from .models import PromotionType


class CampaignCreateForm(forms.Form):
    """Single-form guided campaign creation flow.

    Combines promotion definition and delivery details so a merchant can
    create a CAMPAIGN_APPLY promotion and send the claim link in one step,
    without ever needing to touch the Offer model directly.
    """

    # ── Campaign discount ────────────────────────────────────────────────────

    name = forms.CharField(
        max_length=255,
        label="Promotion name",
        help_text=(
            "Customer-visible name shown in the cart and order confirmation. "
            "Keep it short and benefit-focused, e.g. 'Summer 10% Order Discount'."
        ),
    )
    code = forms.SlugField(
        max_length=64,
        label="Promotion code",
        help_text=(
            "Internal identifier used for logging and campaign linking. "
            "Use lowercase-with-hyphens, e.g. <code>summer-2026-order-10pct</code>. "
            "Must be unique — this code cannot be changed after the campaign is sent."
        ),
    )
    type = forms.ChoiceField(
        choices=PromotionType.choices,
        label="Discount type",
        help_text=(
            "<strong>PERCENT</strong> — percentage off the cart total (e.g. 10 = 10% off). "
            "<strong>FIXED</strong> — fixed amount off the cart total (e.g. 50 = €50 off)."
        ),
    )
    value = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label="Discount value",
        help_text=(
            "The magnitude of the discount. For PERCENT: enter 1–100. "
            "For FIXED: enter the amount in the store currency."
        ),
    )
    minimum_order_value = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.01"),
        label="Minimum order value (optional)",
        help_text=(
            "If set, the promotion only activates once the cart gross total reaches "
            "this value. Leave blank for no minimum spend requirement."
        ),
    )
    is_discoverable = forms.BooleanField(
        required=False,
        label="Surface in storefront messaging",
        help_text=(
            "When checked, this promotion can appear in cart progress banners and "
            "other owned-media nudges. The promotion is applied regardless of this setting."
        ),
    )
    active_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Promotion start date (optional)",
        help_text="Leave blank for no lower bound.",
    )
    active_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Promotion end date (optional)",
        help_text="Leave blank for a promotion with no expiry.",
    )

    # ── Delivery ─────────────────────────────────────────────────────────────

    recipient_email = forms.EmailField(
        label="Recipient email",
        help_text="The claim link will be delivered to this address.",
    )
    offer_active_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Offer expiry date (optional)",
        help_text=(
            "After this date, the offer link will no longer be claimable. "
            "Leave blank for no expiry. Can be earlier than the promotion end date."
        ),
    )

    # ── Validation ───────────────────────────────────────────────────────────

    def clean(self) -> dict:
        cleaned = super().clean()

        type_ = cleaned.get("type")
        value = cleaned.get("value")
        if type_ == PromotionType.PERCENT and value is not None and value > 100:
            self.add_error("value", "Percent promotion value cannot exceed 100.")

        active_from = cleaned.get("active_from")
        active_to = cleaned.get("active_to")
        if active_from and active_to and active_from > active_to:
            self.add_error("active_from", "Promotion start date must not be later than end date.")

        return cleaned
