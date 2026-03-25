"""DEV_FAKE payment provider.

Wraps the existing development/simulation payment behaviour behind the
BasePaymentProvider contract.  It reads 'simulated_result' ("success" or
"fail") from context.extra to determine the outcome synchronously — matching
the legacy POST /payments/ {result: ...} semantics.

This provider must never be used in production.  Its purpose is to keep the
dev/test flow intact while the provider boundary is being established.
"""

from payments.models import Payment
from payments.providers.base import BasePaymentProvider, PaymentStartContext, ProviderStartResult

_SIMULATED_RESULT_KEY = "simulated_result"
_FAILURE_REASON = "Simulated payment failure"


class DevFakeProvider(BasePaymentProvider):
    """Direct, synchronous simulation provider.

    Outcome is determined entirely by context.extra['simulated_result'].
    Defaults to success when the key is absent.
    """

    #: Stable provider enum value — used by orchestration to set Payment.provider.
    provider_enum = Payment.Provider.DEV_FAKE

    def start(self, context: PaymentStartContext) -> ProviderStartResult:
        simulated = context.extra.get(_SIMULATED_RESULT_KEY, "success")

        if simulated == "success":
            return ProviderStartResult(success=True)

        return ProviderStartResult(
            success=False,
            failure_reason=_FAILURE_REASON,
        )
