from api.exceptions.base import ValidationException, ConflictException


class PaymentAlreadyExistsException(ConflictException):
    default_code = "PAYMENT_ALREADY_EXISTS"
    default_detail = "Payment already exists."


class InvalidPaymentResultException(ValidationException):
    default_code = "INVALID_PAYMENT_RESULT"
    default_detail = "Invalid payment result."
