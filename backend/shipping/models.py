from django.db import models

from shipping.statuses import ShipmentStatus


class Shipment(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="shipments",
    )
    provider_code = models.CharField(max_length=50)
    service_code = models.CharField(max_length=50)
    carrier_name_snapshot = models.CharField(max_length=255)
    service_name_snapshot = models.CharField(max_length=255)
    tracking_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    carrier_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.PENDING,
    )
    label_url = models.CharField(
        max_length=2048,
        null=True,
        blank=True,
    )
    receiver_snapshot = models.JSONField(default=dict, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["provider_code", "tracking_number"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Shipment #{self.pk} ({self.status})"


class ShipmentEvent(models.Model):
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=64)
    raw_status = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )
    normalized_status = models.CharField(
        max_length=32,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.PENDING,
    )
    payload = models.JSONField(default=dict, blank=True)
    external_event_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    occurred_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["shipment", "normalized_status"]),
            models.Index(fields=["external_event_id"]),
        ]
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self):
        return f"ShipmentEvent #{self.pk} ({self.event_type})"