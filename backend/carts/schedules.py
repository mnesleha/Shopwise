"""Idempotent django-q2 schedule registration for the carts app.

Call ``register_anonymous_cart_cleanup()`` to ensure the scheduled job
exists in the database.  The function is safe to call multiple times —
it uses ``update_or_create`` keyed on a stable name, so re-running never
produces duplicate rows.

Typical entry point: the ``sync_q_schedules`` management command, which
should be executed once during deployment (or after ``migrate``).
"""

from django.conf import settings
from django_q.models import Schedule

#: Stable identifier used to look up the schedule row.  Never change this
#: value once deployed; doing so would orphan the old row.
ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME = "carts.anonymous_cart_cleanup"


def register_anonymous_cart_cleanup() -> None:
    """Create or update the django-q2 schedule for anonymous cart cleanup.

    Reads cron expression from ``ANONYMOUS_CART_CLEANUP_CRON`` so the
    schedule can be adjusted via environment variable without code changes.

    The actual TTL is *not* stored in the schedule kwargs; instead the job
    function ``carts.jobs.run_anonymous_cart_cleanup`` reads
    ``ANONYMOUS_CART_TTL_DAYS`` from settings at runtime.
    """
    cron: str = getattr(settings, "ANONYMOUS_CART_CLEANUP_CRON", "0 3 * * *")

    Schedule.objects.update_or_create(
        name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME,
        defaults={
            "func": "carts.jobs.run_anonymous_cart_cleanup",
            "schedule_type": Schedule.CRON,
            "cron": cron,
            # repeats=-1 means run indefinitely.
            "repeats": -1,
        },
    )
