from api.exceptions.base import ConflictException


class ProductUnavailableException(ConflictException):
    default_detail = "Product is not available"
    default_code = "product_unavailable"
