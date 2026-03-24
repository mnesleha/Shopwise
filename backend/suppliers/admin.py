import re as _re

from django import forms
from django.contrib import admin

from suppliers.models import Supplier, SupplierAddress, SupplierPaymentDetails


# ---------------------------------------------------------------------------
# Inline formsets — validate "at most one default" across the *submitted* forms
# ---------------------------------------------------------------------------
# Django validates each inline form instance independently before writing
# anything to the DB.  A model-level clean() therefore sees stale DB state
# (the old default is still IN the DB while the new one is being validated),
# which causes a false-positive error when the user changes the default from
# one record to another in a single form submission.
#
# Formset-level clean() runs after all individual forms have been validated and
# has access to every form's *new* cleaned_data, so it can count the intended
# defaults correctly.
# ---------------------------------------------------------------------------


class _AtMostOneDefaultFormSet(forms.BaseInlineFormSet):
    """Reusable base that enforces at most one ``is_default_for_orders=True``
    across the submitted inline forms."""

    _default_field_label = "default for orders"  # overridden by subclasses for messages

    def clean(self) -> None:
        super().clean()
        # Count forms that will have is_default_for_orders=True after saving.
        # Ignore forms that are being deleted or that failed their own validation.
        intended_defaults = [
            form
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get("DELETE", False)
            and form.cleaned_data.get("is_default_for_orders", False)
        ]
        if len(intended_defaults) > 1:
            raise forms.ValidationError(
                f"Only one record can be marked as {self._default_field_label} at a time. "
                f"You have marked {len(intended_defaults)}."
            )


class SupplierAddressInlineFormSet(_AtMostOneDefaultFormSet):
    _default_field_label = "the default order address"


class SupplierPaymentDetailsInlineFormSet(_AtMostOneDefaultFormSet):
    _default_field_label = "the default order payment details"


# ---------------------------------------------------------------------------
# Radio widget for is_default_for_orders
# ---------------------------------------------------------------------------
# Django admin inlines give each row a unique field name
# ("supplieraddress_set-0-is_default_for_orders", "-1-…", …), so the browser
# cannot group the inputs as standard radio buttons.  DefaultRadioWidget
# renders <input type="radio"> and adds data-default-radio with a
# normalised group key; default_radio.js uses that key to uncheck siblings
# whenever a row is selected.
# ---------------------------------------------------------------------------


class DefaultRadioWidget(forms.CheckboxInput):
    """Renders a boolean field as a radio button.

    CheckboxInput.value_from_datadict() already handles the "missing POST key
    means False" case that both checkboxes and radio buttons share, so no
    override is needed there.
    """

    input_type = "radio"

    def get_context(self, name, value, attrs):
        # Derive a stable group key: "prefix-N-fieldname" → "prefix-fieldname"
        group = _re.sub(r"-\d+-", "-", name)
        extra = {"class": "default-radio", "data-default-radio": group}
        merged = {**(attrs or {}), **extra}
        return super().get_context(name, value, merged)


class SupplierAddressInlineForm(forms.ModelForm):
    class Meta:
        model = SupplierAddress
        fields = "__all__"
        widgets = {"is_default_for_orders": DefaultRadioWidget}


class SupplierPaymentDetailsInlineForm(forms.ModelForm):
    class Meta:
        model = SupplierPaymentDetails
        fields = "__all__"
        widgets = {"is_default_for_orders": DefaultRadioWidget}


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------


class SupplierAddressInline(admin.TabularInline):
    model = SupplierAddress
    form = SupplierAddressInlineForm
    formset = SupplierAddressInlineFormSet
    extra = 0
    # is_default_for_orders first so it is visible without horizontal scrolling
    fields = (
        "is_default_for_orders",
        "label",
        "street_line_1",
        "street_line_2",
        "city",
        "postal_code",
        "country",
    )
    readonly_fields = ("created_at", "updated_at")

    class Media:
        js = ("suppliers/admin/default_radio.js",)

    def get_readonly_fields(self, request, obj=None):
        # Show timestamps only when the inline row already exists.
        if obj:
            return ("created_at", "updated_at")
        return ()


class SupplierPaymentDetailsInline(admin.TabularInline):
    model = SupplierPaymentDetails
    form = SupplierPaymentDetailsInlineForm
    formset = SupplierPaymentDetailsInlineFormSet
    extra = 0
    # is_default_for_orders first so it is visible without horizontal scrolling
    fields = (
        "is_default_for_orders",
        "label",
        "bank_name",
        "account_number",
        "iban",
        "swift",
    )
    readonly_fields = ("created_at", "updated_at")

    class Media:
        js = ("suppliers/admin/default_radio.js",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("created_at", "updated_at")
        return ()


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "company_id", "vat_id", "email", "phone", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "company_id", "vat_id", "email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [SupplierAddressInline, SupplierPaymentDetailsInline]

    fieldsets = (
        (
            "Supplier Identity",
            {
                "fields": ("name", "company_id", "vat_id", "email", "phone"),
                "description": (
                    "Core identity fields shown on invoices and order documents."
                ),
            },
        ),
        (
            "Configuration",
            {
                "fields": ("is_active",),
                "description": (
                    "Exactly one supplier must be active at any time. "
                    "The active supplier's default address and default payment details "
                    "are copied into every new order at checkout."
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(SupplierAddress)
class SupplierAddressAdmin(admin.ModelAdmin):
    list_display = (
        "supplier",
        "label",
        "street_line_1",
        "city",
        "country",
        "default_badge",
    )
    list_filter = ("supplier", "is_default_for_orders", "country")
    search_fields = ("supplier__name", "street_line_1", "city")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Supplier",
            {
                "fields": ("supplier",),
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "label",
                    "street_line_1",
                    "street_line_2",
                    "city",
                    "postal_code",
                    "country",
                ),
            },
        ),
        (
            "Order Configuration",
            {
                "fields": ("is_default_for_orders",),
                "description": (
                    "Mark exactly one address per supplier as the default for orders. "
                    "This address is snapshotted into every new order at checkout time. "
                    "Changing this setting does NOT affect existing orders."
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Default for Orders", boolean=True)
    def default_badge(self, obj):
        return obj.is_default_for_orders

    def save_model(self, request, obj, form, change):
        """Radio-button save: marking this address as the default automatically
        clears the flag on all other addresses for the same supplier.
        """
        if obj.is_default_for_orders and obj.supplier_id:
            SupplierAddress.objects.filter(
                supplier_id=obj.supplier_id,
                is_default_for_orders=True,
            ).exclude(pk=obj.pk or 0).update(is_default_for_orders=False)
        super().save_model(request, obj, form, change)


@admin.register(SupplierPaymentDetails)
class SupplierPaymentDetailsAdmin(admin.ModelAdmin):
    list_display = (
        "supplier",
        "label",
        "bank_name",
        "iban",
        "swift",
        "default_badge",
    )
    list_filter = ("supplier", "is_default_for_orders")
    search_fields = ("supplier__name", "bank_name", "iban", "account_number")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Supplier",
            {
                "fields": ("supplier",),
            },
        ),
        (
            "Payment Details",
            {
                "fields": (
                    "label",
                    "bank_name",
                    "account_number",
                    "iban",
                    "swift",
                ),
            },
        ),
        (
            "Order Configuration",
            {
                "fields": ("is_default_for_orders",),
                "description": (
                    "Mark exactly one payment record per supplier as the default for orders. "
                    "These details are snapshotted into every new order at checkout time. "
                    "Changing this setting does NOT affect existing orders."
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Default for Orders", boolean=True)
    def default_badge(self, obj):
        return obj.is_default_for_orders

    def save_model(self, request, obj, form, change):
        """Radio-button save: marking this payment record as the default
        automatically clears the flag on all other payment records for the same
        supplier.
        """
        if obj.is_default_for_orders and obj.supplier_id:
            SupplierPaymentDetails.objects.filter(
                supplier_id=obj.supplier_id,
                is_default_for_orders=True,
            ).exclude(pk=obj.pk or 0).update(is_default_for_orders=False)
        super().save_model(request, obj, form, change)
