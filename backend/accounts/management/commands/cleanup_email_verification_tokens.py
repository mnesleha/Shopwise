from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import EmailVerificationToken


class Command(BaseCommand):
    help = (
        "Delete expired or used email verification tokens beyond a retention window. "
        "Intended for periodic execution (e.g., daily)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days",
            type=int,
            default=7,
            help="Delete tokens that are expired or used older than this many days (default: 7).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print how many tokens would be deleted without deleting them.",
        )

    def handle(self, *args, **options):
        retention_days: int = options["retention_days"]
        dry_run: bool = options["dry_run"]

        now = timezone.now()
        cutoff = now - timedelta(days=retention_days)

        # Delete:
        # - tokens used long ago (used_at < cutoff)
        # - tokens expired long ago (expires_at < cutoff)
        qs = EmailVerificationToken.objects.filter(
            (  # used tokens beyond retention
                # used_at is not null and older than cutoff
            )
        )

        qs = EmailVerificationToken.objects.filter(
            used_at__lt=cutoff
        ) | EmailVerificationToken.objects.filter(
            expires_at__lt=cutoff
        )

        # Convert back to queryset (union returns a combined queryset in Django)
        total = qs.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN: would delete {total} tokens"))
            return

        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {deleted} tokens (matched {total})"))
