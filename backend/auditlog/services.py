from auditlog.models import AuditEvent


class AuditService:
    @staticmethod
    def emit(
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        actor_type: str,
        actor_user=None,
        metadata: dict | None = None,
        context: dict | None = None,
        scope_key: str | None = None,
    ) -> AuditEvent:
        return AuditEvent.objects.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_type=actor_type,
            actor_user=actor_user,
            metadata=metadata or {},
            context=context or {},
            scope_key=scope_key,
        )
