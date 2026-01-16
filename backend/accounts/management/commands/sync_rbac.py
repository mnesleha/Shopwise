from django.core.management.base import BaseCommand, CommandError
from api.exceptions.accounts import MissingRBACPermissionsError
from accounts.rbac import sync_rbac


class Command(BaseCommand):
    help = "Sync RBAC groups and permissions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show planned changes without modifying the database.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Remove permissions not declared in ROLE_PERMISSIONS.",
        )

    def handle(self, *args, **options):
        try:
            summary = sync_rbac(
                dry_run=options["dry_run"],
                strict=options["strict"],
            )
        except MissingRBACPermissionsError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write("RBAC sync summary:")
        self.stdout.write(f"created_groups: {summary['created_groups']}")
        self.stdout.write(f"updated_groups: {summary['updated_groups']}")
        self.stdout.write(f"removed_perms: {summary['removed_perms']}")
