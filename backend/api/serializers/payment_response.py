from rest_framework import serializers

from payments.models import Payment


class PaymentResponseSerializer(serializers.ModelSerializer):
    """
    Response serializer for payment creation.

    Returns payment details after successful payment processing.
    All fields are read-only as this is strictly a response serializer.
    """
    class Meta:
        model = Payment
        fields = ("id", "status", "order")
        read_only_fields = fields
