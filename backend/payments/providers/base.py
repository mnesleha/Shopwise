"""Payment provider base contract and shared value objects."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PaymentStartContext:
    """Input context passed to a provider's start() call.

    Attributes:
        order:   The Order model instance being paid.
        payment: The Payment model instance (already persisted as PENDING).
        extra:   Provider-specific or flow-specific extras (e.g. simulated_result
                 for DEV_FAKE, redirect return URL for hosted providers).
    """

    order: Any
    payment: Any
    extra: dict = field(default_factory=dict)


@dataclass
class ProviderStartResult:
    """Normalized result returned by a provider after start() is called.

    Attributes:
        success:             True if the payment was immediately authorised.
        provider_payment_id: External reference assigned by the provider.
                             None for direct providers and DEV_FAKE.
        failure_reason:      Human-readable reason when success=False.
        redirect_url:        Non-None for hosted/redirect providers; None for
                             direct (synchronous) providers such as DEV_FAKE.
    """

    success: bool
    provider_payment_id: Optional[str] = None
    failure_reason: Optional[str] = None
    redirect_url: Optional[str] = None


class BasePaymentProvider(ABC):
    """Abstract contract for payment provider implementations.

    Every provider must implement start().  Webhook / callback handling will be
    introduced as a separate method when that slice is implemented.
    """

    @abstractmethod
    def start(self, context: PaymentStartContext) -> ProviderStartResult:
        """Initiate a payment attempt.

        Args:
            context: Order, payment, and any provider-specific extras.

        Returns:
            A ProviderStartResult describing the immediate outcome.
        """
        ...
