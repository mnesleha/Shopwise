from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        return response

    # --- Validation errors (serializer, input) ---
    if isinstance(exc, ValidationError):
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "One or more fields have errors.",
                "errors": exc.detail,  # dict: field -> list[str]
            },
            status=response.status_code,
        )

    # --- Domain / business errors ---
    if isinstance(exc, APIException):
        return Response(
            {
                "code": getattr(exc, "default_code", "error"),
                "message": str(exc.detail),
            },
            status=response.status_code,
        )

    return response
