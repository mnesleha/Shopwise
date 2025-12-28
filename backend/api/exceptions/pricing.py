class PricingError(Exception):
    """Base class for pricing-related errors."""


class InvalidQuantityError(PricingError):
    pass


class InvalidPriceError(PricingError):
    pass
