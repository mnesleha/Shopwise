from rest_framework.exceptions import APIException
from rest_framework import status


class ValidationException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error."
    default_code = "VALIDATION_ERROR"


class NotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = "NOT_FOUND"


class ConflictException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict."
    default_code = "CONFLICT"


class InternalServerException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Internal server error."
    default_code = "INTERNAL_ERROR"
