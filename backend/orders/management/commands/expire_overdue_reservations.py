from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from orders.services.inventory_reservation_service import (
    expire_overdue_reservations,
    count_overdue_reservations,
)


class Command(BaseCommand):
    help = "Expire overdue inventory reservations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of",
            dest="as_of",
            help='ISO-8601 datetime with timezone. Example: "2026-01-13T12:00:00Z". '
                 "Defaults to current time.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Do not perform any updates; only print how many reservations would be expired.",
        )

    def handle(self, *args, **options):
        as_of_raw = options.get("as_of")
        if as_of_raw:
            as_of = parse_datetime(as_of_raw)
            if as_of is None or not timezone.is_aware(as_of):
                raise CommandError(
                    "Invalid --as-of value. Provide ISO-8601 datetime with timezone."
                )
        else:
            as_of = timezone.now()

        if options.get("dry_run"):
            would_expire = count_overdue_reservations(now=as_of)
            self.stdout.write(f"Would expire {would_expire} reservations.")
            return

        expired_count = expire_overdue_reservations(now=as_of)
        self.stdout.write(f"Expired {expired_count} reservations.")
