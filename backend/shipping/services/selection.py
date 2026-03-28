from shipping.providers.resolver import (
    ProviderNotConfiguredException,
    resolve_provider,
)


class InvalidShippingServiceSelection(Exception):
    def __init__(self, *, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


def resolve_shipping_service_selection(*, provider_code: str, service_code: str, order=None):
    try:
        provider = resolve_provider(provider_code)
    except ProviderNotConfiguredException as exc:
        raise InvalidShippingServiceSelection(
            field="shipping_provider_code",
            message="Unknown shipping provider.",
        ) from exc

    services = provider.list_services(order=order)
    for service in services:
        if service.service_code == service_code:
            return service

    raise InvalidShippingServiceSelection(
        field="shipping_service_code",
        message="Unknown shipping service for provider.",
    )