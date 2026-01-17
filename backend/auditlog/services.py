import logging
from auditlog.models import AuditEvent


logger = logging.getLogger(__name__)


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
        fail_silently: bool = False,
    ) -> AuditEvent | None:
        """Create an audit event.

        MVP policy: audit logging must not block critical business flows.
        When fail_silently=True, any exception during audit write is swallowed
        and the method returns None.
        """

        try:
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
        except Exception:
            if not fail_silently:
                raise
            logger.warning(
                "AuditEvent write failed (best-effort). action=%s entity=%s:%s actor_type=%s",
                action,
                entity_type,
                entity_id,
                actor_type,
                exc_info=True,
            )
            return None
