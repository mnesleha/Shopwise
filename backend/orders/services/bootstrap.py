"""
Guest-order bootstrap service.

Provides address seeding from an order snapshot into a new customer profile.
Called best-effort only — failures are logged but never re-raised so that
account creation succeeds even when snapshot data is incomplete or missing.
"""
import logging

from django_countries import countries as _country_db

from accounts.models import Address, CustomerProfile
from orders.models import Order

logger = logging.getLogger(__name__)


def _normalize_country(value: str) -> str:
    """
    Normalise a country value to a 2-char ISO 3166-1 alpha-2 code.

    Accepts:
    - A correct 2-char code ("CZ", "cz") → returned upper-cased.
    - A full country name ("Czech Republic") → resolved via django-countries.
    - Anything unrecognisable → returns "" (CountryField accepts blank).
    """
    if not value:
        return ""
    stripped = value.strip()
    upper = stripped.upper()
    # Fast path: already a valid 2-char code.
    if upper in _country_db:
        return upper
    # Slow path: try to resolve a full country name.
    code = _country_db.by_name(stripped)
    if not code:
        # Try common alternative casings (e.g. all-upper "CZECH REPUBLIC").
        code = _country_db.by_name(stripped.title())
    return code or ""


def seed_addresses_from_order(*, user, order: Order) -> None:
    """
    Seed CustomerProfile addresses from an order's shipping/billing snapshot.

    Creates a default shipping address (and, when billing differs from
    shipping, a separate default billing address) on the user's profile.
    Sets both as the profile's default addresses.

    Best-effort: any exception is logged and swallowed; the caller must NOT
    rely on this function succeeding.
    """
    try:
        profile, _ = CustomerProfile.objects.get_or_create(user=user)

        shipping_addr = Address.objects.create(
            profile=profile,
            first_name=order.shipping_first_name or "",
            last_name=order.shipping_last_name or "",
            street_line_1=order.shipping_address_line1 or "",
            street_line_2=order.shipping_address_line2 or "",
            city=order.shipping_city or "",
            postal_code=order.shipping_postal_code or "",
            country=_normalize_country(order.shipping_country or ""),
            phone=order.shipping_phone or "",
            company=order.shipping_company or "",
            company_id=order.shipping_company_id or "",
            vat_id=order.shipping_vat_id or "",
        )
        profile.default_shipping_address = shipping_addr

        if order.billing_same_as_shipping or not order.billing_address_line1:
            # Billing same as shipping: create a separate Address copy so
            # both FK slots are populated and can be updated independently.
            billing_addr = Address.objects.create(
                profile=profile,
                first_name=order.shipping_first_name or "",
                last_name=order.shipping_last_name or "",
                street_line_1=order.shipping_address_line1 or "",
                street_line_2=order.shipping_address_line2 or "",
                city=order.shipping_city or "",
                postal_code=order.shipping_postal_code or "",
                country=_normalize_country(order.shipping_country or ""),
                phone=order.shipping_phone or "",
                company=order.shipping_company or "",
                company_id=order.shipping_company_id or "",
                vat_id=order.shipping_vat_id or "",
            )
        else:
            billing_addr = Address.objects.create(
                profile=profile,
                first_name=order.billing_first_name or order.shipping_first_name or "",
                last_name=order.billing_last_name or order.shipping_last_name or "",
                street_line_1=order.billing_address_line1 or "",
                street_line_2=order.billing_address_line2 or "",
                city=order.billing_city or "",
                postal_code=order.billing_postal_code or "",
                country=_normalize_country(order.billing_country or ""),
                phone=order.billing_phone or order.shipping_phone or "",
                company=order.billing_company or "",
                company_id=order.billing_company_id or "",
                vat_id=order.billing_vat_id or "",
            )

        profile.default_billing_address = billing_addr
        profile.save(
            update_fields=["default_shipping_address", "default_billing_address"]
        )

    except Exception:
        logger.exception(
            "Failed to seed profile addresses from order %s for user %s",
            getattr(order, "pk", None),
            getattr(user, "pk", None),
        )
