from api.exceptions.base import ConflictException


class PaymentAlreadyExistsException(ConflictException):
    default_code = "PAYMENT_ALREADY_EXISTS"
    default_detail = "Payment already exists."


class OrderNotPayableException(ConflictException):
    """
    Raised when a payment is attempted on an order that is not in a payable state.
    """
    default_detail = "Order is not payable in its current state."
    default_code = "ORDER_NOT_PAYABLE"
