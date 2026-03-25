"""Payment orchestration service.

Provides the top-level application entrypoint for starting a payment against
an order.  Orchestrates:
  1. Guard checks (payable state, duplicate success)
  2. Provider resolution via the resolver
  3. PENDING payment creation
  4. Provider start call
  5. Result application (delegated to payment_result_applier)

This service is the intended call site for future checkout wiring and for
any caller that needs a clean, provider-agnostic "start payment" operation.

The legacy OrderService.create_payment_and_apply_result() delegates here to
preserve backward compatibility.
"""

from __future__ import annotations

from typing import Optional

from django.db import transaction

from api.exceptions.payment import OrderNotPayableException, PaymentAlreadyExistsException
from orders.models import Order
from payments.models import Payment
from payments.providers.base import PaymentStartContext
from payments.providers.resolver import resolve_provider
from payments.services.payment_result_applier import apply_provider_result

# Maps concrete provider classes to the Payment.Provider enum value recorded
# on the payment record.  Add new entries here when new providers are introduced.
_PROVIDER_CLASS_TO_ENUM = {
    "DevFakeProvider": Payment.Provider.DEV_FAKE,
    "AcquireMockProvider": Payment.Provider.ACQUIREMOCK,
}


class PaymentOrchestrationService:

    @staticmethod
    def start_payment(
        *,
        order: Order,
        payment_method: Optional[str],
        extra: Optional[dict] = None,
    ) -> Payment:
        """Start a payment for an order and apply the provider result.

        Args:
            order:          The Order to be paid.
            payment_method: Business-facing payment method (Payment.PaymentMethod),
                            or None for legacy / unset cases.
            extra:          Provider-specific context (e.g. ``simulated_result``
                            for DEV_FAKE, redirect URL for hosted providers).
                            Defaults to an empty dict.

        Returns:
            The persisted Payment record with final status applied.

        Raises:
            ProviderNotConfiguredException: If no provider is mapped to
                                            the given payment_method.
            PaymentAlreadyExistsException:  If a SUCCESS payment already exists.
            OrderNotPayableException:       If the order is not in a payable state.
        """
        if extra is None:
            extra = {}

        # Resolve provider early — fail fast if the method has no backing provider.
        provider = resolve_provider(payment_method)

        with transaction.atomic():
            # Re-fetch with a row lock to prevent races.
            locked_order = (
                Order.objects.select_for_update()
                .filter(id=order.id)
                .first()
            )
            if not locked_order:
                raise OrderNotPayableException()

            # Block duplicate success payments before checking order status.
            if Payment.objects.filter(
                order=locked_order,
                status=Payment.Status.SUCCESS,
            ).exists():
                raise PaymentAlreadyExistsException()

            # Payable states: first attempt (CREATED) or retry (PAYMENT_FAILED).
            if locked_order.status not in (Order.Status.CREATED, Order.Status.PAYMENT_FAILED):
                raise OrderNotPayableException()

            # Create the payment record in PENDING state.
            # Derive the provider enum value from the resolved concrete class.
            provider_enum = _PROVIDER_CLASS_TO_ENUM.get(
                type(provider).__name__, Payment.Provider.DEV_FAKE
            )
            payment = Payment.objects.create(
                order=locked_order,
                status=Payment.Status.PENDING,
                payment_method=payment_method,
                provider=provider_enum,
            )

            context = PaymentStartContext(
                order=locked_order,
                payment=payment,
                extra=extra,
            )
            provider_result = provider.start(context)

            apply_provider_result(
                payment=payment,
                order=locked_order,
                provider_result=provider_result,
            )

            return payment
