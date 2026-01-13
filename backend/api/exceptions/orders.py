from api.exceptions.base import ConflictException


class OutOfStockException(ConflictException):
    default_code = "OUT_OF_STOCK"
    default_detail = "Insufficient stock to reserve items."
