"""Payment provider resolver.

Maps a business-facing payment method (Payment.PaymentMethod) to a concrete
provider instance.  Extend the mapping here when new providers are introduced.
"""

from __future__ import annotations

from typing import Optional

from payments.models import Payment
from payments.providers.base import BasePaymentProvider
from payments.providers.dev_fake import DevFakeProvider
from payments.providers.acquiremock import AcquireMockProvider


class ProviderNotConfiguredException(Exception):
    """Raised when no provider is configured for a given payment method."""


def resolve_provider(payment_method: Optional[str]) -> BasePaymentProvider:
    """Return the provider instance responsible for the given payment method.

    Args:
        payment_method: A value from Payment.PaymentMethod, or None for legacy
                        records where no method was recorded.

    Returns:
        A concrete BasePaymentProvider instance ready to handle the payment.

    Raises:
        ProviderNotConfiguredException: If no provider is mapped to the method.
    """
    if payment_method in (Payment.PaymentMethod.COD, None):
        return DevFakeProvider()

    if payment_method == Payment.PaymentMethod.CARD:
        return AcquireMockProvider()

    raise ProviderNotConfiguredException(
        f"Unknown payment method: {payment_method!r}"
    )
