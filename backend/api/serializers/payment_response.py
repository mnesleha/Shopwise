from rest_framework import serializers

from payments.models import Payment


class PaymentResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "status", "order")
        read_only_fields = fields
