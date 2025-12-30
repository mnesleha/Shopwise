from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standard error response schema.

    Used to document error responses returned by the API.
    """
    code = serializers.CharField()
    message = serializers.CharField()
    errors = serializers.DictField(
        child=serializers.ListField(
            child=serializers.CharField()
        ),
        required=False,
    )
