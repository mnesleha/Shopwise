from __future__ import annotations

from django.core.management.base import BaseCommand

from utils.seed.demo.seed import run_demo_seed
from utils.seed.dev.seed import run_dev_seed


RUNNERS = {
    "demo": run_demo_seed,
    "dev": run_dev_seed,
}


class Command(BaseCommand):
    help = "Seed Shopwise data for an explicit profile."

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            choices=sorted(RUNNERS.keys()),
            default="dev",
            help="Seed profile to execute. Supported profiles: demo, dev.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete relevant data before seeding the selected profile.",
        )
        parser.add_argument(
            "--export-fixtures",
            default=None,
            help="Write a fixtures JSON map to this path.",
        )

    def handle(self, *args, **options):
        profile = options["profile"]
        runner = RUNNERS[profile]

        runner(
            reset=options["reset"],
            export_path=options["export_fixtures"],
            write_line=self.stdout.write,
        )

        self.stdout.write(self.style.SUCCESS(f"Seed completed for profile '{profile}'."))