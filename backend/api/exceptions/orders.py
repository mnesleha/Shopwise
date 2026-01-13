from api.exceptions.base import ConflictException


class OutOfStockException(ConflictException):
    default_code = "OUT_OF_STOCK"
    default_detail = "Insufficient stock to reserve items."


class ReservationAlreadyExistsException(ConflictException):
    default_code = "RESERVATION_ALREADY_EXISTS"
    default_detail = "Reservations already exist for this order."


class InvalidOrderStateException(ConflictException):
    default_code = "INVALID_ORDER_STATE"
    default_detail = "Order is not in a state that allows this operation."
