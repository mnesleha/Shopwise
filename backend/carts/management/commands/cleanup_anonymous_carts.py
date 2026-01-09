from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from carts.models import Cart


class Command(BaseCommand):
    help = "Delete expired anonymous carts using a TTL in days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Delete carts created more than N days ago (default: 7).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many carts would be deleted without deleting.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        cutoff = timezone.now() - timedelta(days=days)

        queryset = Cart.objects.filter(
            user__isnull=True,
            created_at__lt=cutoff,
        ).filter(
            Q(status=Cart.Status.ACTIVE) | Q(status=Cart.Status.MERGED)
        )
        count = queryset.count()

        if options["dry_run"]:
            self.stdout.write(
                f"[dry-run] {count} anonymous active carts older than {days} days"
            )
            return

        deleted, _ = queryset.delete()
        self.stdout.write(
            f"Deleted {deleted} anonymous active carts older than {days} days"
        )
