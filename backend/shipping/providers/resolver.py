from shipping.providers.base import BaseShippingProvider
from shipping.providers.mock import MockShippingProvider


class ProviderNotConfiguredException(Exception):
    pass


def resolve_provider(provider_code: str | None) -> BaseShippingProvider:
    if provider_code == MockShippingProvider.provider_code:
        return MockShippingProvider()

    raise ProviderNotConfiguredException(
        f"Unknown shipping provider: {provider_code!r}"
    )