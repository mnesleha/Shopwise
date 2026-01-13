from rest_framework import serializers

from orders.models import InventoryReservation


class InventoryReservationAdminSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(read_only=True)
    product_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = InventoryReservation
        fields = [
            "id",
            "order_id",
            "product_id",
            "quantity",
            "status",
            "expires_at",
            "committed_at",
            "released_at",
            "release_reason",
        ]
