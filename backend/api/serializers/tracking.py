from rest_framework import serializers


class ShipmentTimelineEntrySerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    occurred_at = serializers.CharField(read_only=True, allow_null=True)
    is_current = serializers.BooleanField(read_only=True)


class PublicTrackingResponseSerializer(serializers.Serializer):
    tracking_number = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    carrier_name = serializers.CharField(read_only=True)
    service_name = serializers.CharField(read_only=True)
    shipment_timeline = ShipmentTimelineEntrySerializer(many=True, read_only=True)