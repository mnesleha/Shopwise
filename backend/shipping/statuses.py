from django.db import models


class ShipmentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    LABEL_CREATED = "LABEL_CREATED", "Label created"
    IN_TRANSIT = "IN_TRANSIT", "In transit"
    DELIVERED = "DELIVERED", "Delivered"
    FAILED_DELIVERY = "FAILED_DELIVERY", "Failed delivery"
    CANCELLED = "CANCELLED", "Cancelled"