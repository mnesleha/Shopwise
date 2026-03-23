"""
Supplier configuration resolution for order creation.

This module provides the single authoritative function for resolving
the active supplier snapshot at order creation time.  It encapsulates
all validation logic so that checkout code has a clean, explicit
failure surface with meaningful error messages.
"""

from __future__ import annotations

from dataclasses import dataclass

from rest_framework import status
from rest_framework.exceptions import APIException

from suppliers.models import Supplier, SupplierAddress, SupplierPaymentDetails


class SupplierConfigurationError(APIException):
    """
    Raised when required supplier configuration for order creation is
    missing or invalid.

    Returns HTTP 503 so that calling code and monitoring can distinguish
    a configuration / operational issue from an application bug (500) or
    invalid input (400/409).
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "SUPPLIER_CONFIGURATION_ERROR"
    default_detail = (
        "Supplier configuration required for order creation is missing or invalid. "
        "Please configure a supplier in Django admin before accepting orders."
    )


@dataclass
class SupplierSnapshot:
    """Immutable supplier data captured at order creation time."""

    # Identity
    name: str
    company_id: str
    vat_id: str
    email: str
    phone: str

    # Address
    street_line_1: str
    street_line_2: str
    city: str
    postal_code: str
    country: str

    # Payment
    bank_name: str
    account_number: str
    iban: str
    swift: str


def resolve_order_supplier_snapshot() -> SupplierSnapshot:
    """
    Resolve the active supplier configuration for a new order snapshot.

    Resolution rules:
    - Exactly one ``Supplier`` with ``is_active=True`` must exist.
    - That supplier must have exactly one ``SupplierAddress`` where
      ``is_default_for_orders=True``.
    - That supplier must have exactly one ``SupplierPaymentDetails`` where
      ``is_default_for_orders=True``.

    Raises:
        SupplierConfigurationError: if any of the invariants above are violated.
            The error message is merchant-readable and points directly at the
            misconfiguration so that Django admin can be used to fix it.

    Returns:
        SupplierSnapshot — an immutable snapshot ready to be written to the order.
    """
    active_suppliers = list(Supplier.objects.filter(is_active=True))

    if not active_suppliers:
        raise SupplierConfigurationError(
            "No active supplier is configured. "
            "Please activate a supplier in Django admin before accepting orders."
        )

    if len(active_suppliers) > 1:
        names = ", ".join(s.name for s in active_suppliers)
        raise SupplierConfigurationError(
            f"{len(active_suppliers)} active suppliers found ({names}). "
            "Exactly one supplier must be active for order creation. "
            "Please deactivate all but one supplier in Django admin."
        )

    supplier = active_suppliers[0]

    # --- address resolution ---
    default_addresses = list(
        SupplierAddress.objects.filter(
            supplier=supplier,
            is_default_for_orders=True,
        )
    )

    if len(default_addresses) == 0:
        raise SupplierConfigurationError(
            f"Supplier '{supplier.name}' has no default order address. "
            "Please mark exactly one address as 'default for orders' in Django admin."
        )

    if len(default_addresses) > 1:
        raise SupplierConfigurationError(
            f"Supplier '{supplier.name}' has {len(default_addresses)} addresses marked "
            "as default for orders; exactly one is required. "
            "Please unmark the extra defaults in Django admin."
        )

    # --- payment details resolution ---
    default_payments = list(
        SupplierPaymentDetails.objects.filter(
            supplier=supplier,
            is_default_for_orders=True,
        )
    )

    if len(default_payments) == 0:
        raise SupplierConfigurationError(
            f"Supplier '{supplier.name}' has no default payment details. "
            "Please mark exactly one payment record as 'default for orders' in Django admin."
        )

    if len(default_payments) > 1:
        raise SupplierConfigurationError(
            f"Supplier '{supplier.name}' has {len(default_payments)} payment records marked "
            "as default for orders; exactly one is required. "
            "Please unmark the extra defaults in Django admin."
        )

    addr = default_addresses[0]
    payment = default_payments[0]

    return SupplierSnapshot(
        name=supplier.name,
        company_id=supplier.company_id,
        vat_id=supplier.vat_id,
        email=supplier.email,
        phone=supplier.phone,
        street_line_1=addr.street_line_1,
        street_line_2=addr.street_line_2,
        city=addr.city,
        postal_code=addr.postal_code,
        country=addr.country,
        bank_name=payment.bank_name,
        account_number=payment.account_number,
        iban=payment.iban,
        swift=payment.swift,
    )
