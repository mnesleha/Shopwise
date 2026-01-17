from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """
    AuditEvent is a best-effort business audit record.

    Notes:
    - `action` is intentionally NOT a Django choices field because audit actions are an evolving taxonomy.
    - `scope_key` and `context` are tenant-friendly placeholders (no multi-tenant behavior in MVP).
    """

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
            models.Index(fields=["action"]),
            models.Index(fields=["actor_type"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}:{self.entity_id} ({self.actor_type})"
