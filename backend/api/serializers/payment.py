from rest_framework import serializers


class PaymentCreateRequestSerializer(serializers.Serializer):
    """
    Request payload for creating a payment (fake gateway simulation).
    """
    order_id = serializers.IntegerField(
        help_text="ID of the order to be paid. Order must be in CREATED status."
    )
    result = serializers.ChoiceField(
        choices=["success", "fail"],
        help_text="Simulated payment result."
    )
