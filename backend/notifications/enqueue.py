from __future__ import annotations

from typing import Any

from django_q.tasks import async_task

from notifications.error_handler import NotificationErrorHandler
from notifications.exceptions import NotificationSendError


def enqueue_best_effort(job: str, **kwargs: Any) -> None:
    """Enqueue a Django-Q2 job with best-effort semantics.

    This must never raise (mirrors AuditService.emit fail-silently pattern).
    """
    try:
        async_task(job, **kwargs)
    except Exception:
        NotificationErrorHandler.handle(
            NotificationSendError(
                code="NOTIFICATION_ENQUEUE_FAILED",
                message="Failed to enqueue notification job.",
                context={"job": job, **kwargs},
            )
        )
