"""DEV_FAKE payment provider.

Wraps the existing development/simulation payment behaviour behind the
BasePaymentProvider contract.  It reads 'simulated_result' ("success" or
"fail") from context.extra to determine the outcome synchronously — matching
the legacy POST /payments/ {result: ...} semantics.

When 'simulated_result' is absent (e.g. COD checkout from the front-end),
the provider returns a *deferred* result: success=True but deferred=True.
This leaves the payment PENDING and the order in CREATED state, waiting for
an explicit confirmation via POST /payments/.

This provider must never be used in production.  Its purpose is to keep the
dev/test flow intact while the provider boundary is being established.
"""

from payments.models import Payment
from payments.providers.base import BasePaymentProvider, PaymentStartContext, ProviderStartResult

_SIMULATED_RESULT_KEY = "simulated_result"
_FAILURE_REASON = "Simulated payment failure"


class DevFakeProvider(BasePaymentProvider):
    """Direct, synchronous simulation provider.

    Outcome is determined by context.extra['simulated_result']:
    - "success" → immediate SUCCESS / PAID (explicit dev simulation).
    - "fail"    → FAILED / PAYMENT_FAILED.
    - absent    → deferred: payment stays PENDING, order stays CREATED.
                  Finalisation requires an explicit POST /payments/ call.
    """

    #: Stable provider enum value — used by orchestration to set Payment.provider.
    provider_enum = Payment.Provider.DEV_FAKE

    def start(self, context: PaymentStartContext) -> ProviderStartResult:
        simulated = context.extra.get(_SIMULATED_RESULT_KEY)

        if simulated is None:
            # No explicit result supplied (e.g. COD from checkout).
            # Defer finalisation: leave payment PENDING, order CREATED.
            # The caller must confirm via the /payments/ endpoint.
            return ProviderStartResult(success=True, deferred=True)

        if simulated == "success":
            return ProviderStartResult(success=True)

        return ProviderStartResult(
            success=False,
            failure_reason=_FAILURE_REASON,
        )
