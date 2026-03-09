"""Management command: register all carts django-q2 scheduled jobs.

Run this command once after ``migrate`` during deployment to ensure all
cron-based scheduled tasks exist in the database.  Re-running is safe —
registrations are idempotent.

Usage::

    python manage.py sync_q_schedules

Future scheduled jobs (e.g. overdue reservation cleanup) should be wired
through this command by adding their registration calls below.
"""

from django.core.management.base import BaseCommand

from carts.schedules import register_anonymous_cart_cleanup


class Command(BaseCommand):
    help = "Create or update all carts django-q2 scheduled jobs (idempotent)."

    def handle(self, *args, **options) -> None:
        register_anonymous_cart_cleanup()
        self.stdout.write(
            self.style.SUCCESS("Registered: anonymous cart cleanup schedule.")
        )
