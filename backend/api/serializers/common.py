from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standard error response schema.

    Used to document error responses returned by the API.
    """
    detail = serializers.CharField(
        help_text="Human-readable description of the error."
    )
