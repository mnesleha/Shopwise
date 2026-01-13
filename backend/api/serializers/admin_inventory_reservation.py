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
            "created_at",
            "expires_at",
            "committed_at",
            "released_at",
            "release_reason",
        ]
        read_only_fields = fields
