from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    class ActorType(models.TextChoices):
        SYSTEM = "system", "System"
        CUSTOMER = "customer", "Customer"
        ADMIN = "admin", "Admin"

    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64)
    action = models.CharField(max_length=128)
    actor_type = models.CharField(max_length=16, choices=ActorType.choices)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    actor_identifier = models.CharField(max_length=128, null=True, blank=True)
    metadata = models.JSONField(default=dict)
    context = models.JSONField(default=dict)
    scope_key = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["created_at"]),
        ]
