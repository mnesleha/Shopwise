"""Idempotent django-q2 schedule registration for the orders app.

Call ``register_overdue_reservation_expiration()`` to ensure the scheduled
job exists in the database.  Idempotent: ``update_or_create`` is keyed on a
stable name so repeated calls never produce duplicate rows.

Typical entry point: the project-wide ``sync_q_schedules`` management command,
which is executed once during deployment (after ``migrate``).
"""

from django.conf import settings
from django_q.models import Schedule

#: Stable identifier used to look up the schedule row.  Never change this
#: value once deployed; doing so would orphan the old row.
OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME = (
    "orders.overdue_reservation_expiration"
)


def register_overdue_reservation_expiration() -> None:
    """Create or update the django-q2 schedule for overdue reservation expiration.

    Reads the cron expression from ``OVERDUE_RESERVATIONS_CLEANUP_CRON`` so
    the schedule frequency can be tuned via environment variable without code
    changes.

    The job function ``orders.jobs.run_overdue_reservation_expiration`` always
    uses ``timezone.now()`` internally (no config parameters needed at the
    schedule level).
    """
    cron: str = getattr(
        settings, "OVERDUE_RESERVATIONS_CLEANUP_CRON", "*/15 * * * *"
    )

    Schedule.objects.update_or_create(
        name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME,
        defaults={
            "func": "orders.jobs.run_overdue_reservation_expiration",
            "schedule_type": Schedule.CRON,
            "cron": cron,
            # repeats=-1 means run indefinitely.
            "repeats": -1,
        },
    )
