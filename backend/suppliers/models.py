from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class Supplier(models.Model):
    """Canonical supplier identity used as the seller / issuer on orders."""

    name = models.CharField(max_length=255)
    company_id = models.CharField(max_length=64, blank=True, help_text="Business registration number (IČO etc.)")
    vat_id = models.CharField(max_length=64, blank=True, help_text="VAT registration number (DIČ etc.)")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Only an active supplier is used for new orders. "
            "Exactly one supplier must be active at any time."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"


class SupplierAddress(models.Model):
    """Postal / registered address for a supplier."""

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    label = models.CharField(
        max_length=64,
        blank=True,
        help_text="Optional label, e.g. 'HQ' or 'Prague Office'.",
    )
    street_line_1 = models.CharField(max_length=255)
    street_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=64)
    country = models.CharField(max_length=64, help_text="ISO 3166-1 alpha-2 country code or full name.")
    is_default_for_orders = models.BooleanField(
        default=False,
        help_text=(
            "Mark exactly one address per supplier as the default for order snapshots. "
            "This address is copied into every new order at checkout time."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        super().clean()
        # Cross-record duplicate-default validation is intentionally NOT performed
        # here because model.clean() is called per-instance before siblings are
        # saved, which makes it impossible to change the default from one record
        # to another in a single admin form submission.
        #
        # Enforcement is instead done at two levels:
        #   1. Admin inline formset (SupplierAddressInlineFormSet) — checks all
        #      submitted forms together before any DB write.
        #   2. Admin save_model override in SupplierAddressAdmin — auto-clears the
        #      old default when a new one is saved (radio-button behaviour).
        #   3. suppliers.services.resolve_order_supplier_snapshot() — raises a clear
        #      503 at checkout time if the DB ends up in an inconsistent state.

    def __str__(self) -> str:
        parts = [p for p in [self.street_line_1, self.city, self.country] if p]
        display = ", ".join(parts)
        if self.label:
            display = f"{self.label}: {display}"
        if self.is_default_for_orders:
            display += " [default]"
        return display

    class Meta:
        verbose_name = "Supplier Address"
        verbose_name_plural = "Supplier Addresses"


class SupplierPaymentDetails(models.Model):
    """Bank / payment details for a supplier — shown on invoices."""

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="payment_details",
    )
    label = models.CharField(
        max_length=64,
        blank=True,
        help_text="Optional label, e.g. 'CZK Account' or 'EUR Account'.",
    )
    bank_name = models.CharField(max_length=255, blank=True)
    account_number = models.CharField(max_length=64, blank=True)
    iban = models.CharField(max_length=64, blank=True)
    swift = models.CharField(max_length=32, blank=True)
    is_default_for_orders = models.BooleanField(
        default=False,
        help_text=(
            "Mark exactly one payment record per supplier as the default for order snapshots. "
            "These details are copied into every new order at checkout time."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        super().clean()
        # Cross-record duplicate-default validation is intentionally NOT performed
        # here — see the equivalent comment in SupplierAddress.clean() for the
        # full rationale.  Enforcement lives in the admin formset and save_model.

    def __str__(self) -> str:
        parts = []
        if self.label:
            parts.append(self.label)
        if self.iban:
            parts.append(f"IBAN: {self.iban}")
        elif self.account_number:
            parts.append(f"Acct: {self.account_number}")
        display = " | ".join(parts) if parts else "Payment details"
        if self.is_default_for_orders:
            display += " [default]"
        return display

    class Meta:
        verbose_name = "Supplier Payment Details"
        verbose_name_plural = "Supplier Payment Details"
