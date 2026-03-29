import os

from django.db import models
from django.utils.text import get_valid_filename

from shipping.statuses import ShipmentStatus


SHIPMENT_STATUS_LABELS = {
    ShipmentStatus.PENDING: "Pending",
    ShipmentStatus.LABEL_CREATED: "Label created",
    ShipmentStatus.IN_TRANSIT: "In transit",
    ShipmentStatus.DELIVERED: "Delivered",
    ShipmentStatus.FAILED_DELIVERY: "Failed delivery",
    ShipmentStatus.CANCELLED: "Cancelled",
}

SHIPMENT_STATUS_SORT_ORDER = {
    ShipmentStatus.PENDING: 10,
    ShipmentStatus.LABEL_CREATED: 20,
    ShipmentStatus.IN_TRANSIT: 30,
    ShipmentStatus.FAILED_DELIVERY: 40,
    ShipmentStatus.DELIVERED: 50,
    ShipmentStatus.CANCELLED: 60,
}

CUSTOMER_TIMELINE_STATUSES = (
    ShipmentStatus.LABEL_CREATED,
    ShipmentStatus.IN_TRANSIT,
    ShipmentStatus.DELIVERED,
)


def shipment_label_upload_to(instance, filename: str) -> str:
    extension = os.path.splitext(filename)[1] or ".svg"
    base_name = instance.tracking_number or f"order-{instance.order_id}-label"
    safe_name = get_valid_filename(base_name.replace(":", "-"))
    return f"shipping/labels/order-{instance.order_id}/{safe_name}{extension}"


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
    label_file = models.FileField(
        upload_to=shipment_label_upload_to,
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

    def get_label_url(self, request=None) -> str | None:
        storage_url = None
        if self.label_file:
            try:
                storage_url = self.label_file.url
            except ValueError:
                storage_url = None

        resolved_url = storage_url or self.label_url
        if resolved_url and request is not None and resolved_url.startswith("/"):
            return request.build_absolute_uri(resolved_url)
        return resolved_url

    def get_timeline(self) -> list[dict]:
        timeline_points: dict[str, object] = {
            ShipmentStatus.LABEL_CREATED: self._timeline_status_time(ShipmentStatus.LABEL_CREATED),
            ShipmentStatus.IN_TRANSIT: self._timeline_status_time(ShipmentStatus.IN_TRANSIT),
            ShipmentStatus.DELIVERED: self._timeline_status_time(ShipmentStatus.DELIVERED),
        }

        for event in sorted(
            self.events.all(),
            key=lambda item: (
                item.occurred_at or item.processed_at or item.created_at,
                item.pk,
            ),
        ):
            if event.normalized_status not in CUSTOMER_TIMELINE_STATUSES:
                continue

            event_time = event.occurred_at or event.processed_at or event.created_at
            existing_time = timeline_points.get(event.normalized_status)
            if existing_time is None or (
                event_time is not None and event_time < existing_time
            ):
                timeline_points[event.normalized_status] = event_time

        current_status = self._current_customer_timeline_status()
        current_status_time = self._timeline_status_time(current_status)
        if timeline_points[current_status] is None:
            timeline_points[current_status] = current_status_time

        return [
            {
                "status": status,
                "label": SHIPMENT_STATUS_LABELS.get(status, status),
                "occurred_at": occurred_at.isoformat() if occurred_at else None,
                "is_current": status == current_status,
            }
            for status, occurred_at in (
                (status, timeline_points.get(status))
                for status in CUSTOMER_TIMELINE_STATUSES
            )
        ]

    def _current_customer_timeline_status(self) -> str:
        if self.status == ShipmentStatus.DELIVERED:
            return ShipmentStatus.DELIVERED
        if self.status in (ShipmentStatus.IN_TRANSIT, ShipmentStatus.FAILED_DELIVERY):
            return ShipmentStatus.IN_TRANSIT
        if self.delivered_at:
            return ShipmentStatus.DELIVERED
        if self.shipped_at:
            return ShipmentStatus.IN_TRANSIT
        return ShipmentStatus.LABEL_CREATED

    def _timeline_status_time(self, status: str):
        if status == ShipmentStatus.DELIVERED:
            if self.delivered_at:
                return self.delivered_at
            if self.status == ShipmentStatus.DELIVERED:
                return self.updated_at or self.shipped_at or self.created_at
            return None
        if status == ShipmentStatus.IN_TRANSIT:
            return self.shipped_at or self.updated_at or self.created_at
        if status == ShipmentStatus.LABEL_CREATED:
            return self.created_at
        return self.updated_at or self.created_at


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