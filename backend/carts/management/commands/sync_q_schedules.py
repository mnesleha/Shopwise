"""Management command: register all django-q2 scheduled jobs for the entire project.

Run this command once after ``migrate`` during deployment to ensure all
cron-based scheduled tasks exist in the database.  Re-running is safe —
registrations are idempotent.

Usage::

    python manage.py sync_q_schedules

Add future scheduled jobs (e.g. report generation, data exports) by importing
their registration function and calling it in ``handle()`` below.
"""

from django.core.management.base import BaseCommand

from carts.schedules import register_anonymous_cart_cleanup
from orders.schedules import register_overdue_reservation_expiration


class Command(BaseCommand):
    help = "Create or update all django-q2 scheduled jobs (idempotent)."

    def handle(self, *args, **options) -> None:
        register_anonymous_cart_cleanup()
        self.stdout.write(
            self.style.SUCCESS("Registered: anonymous cart cleanup schedule.")
        )

        register_overdue_reservation_expiration()
        self.stdout.write(
            self.style.SUCCESS(
                "Registered: overdue reservation expiration schedule."
            )
        )
