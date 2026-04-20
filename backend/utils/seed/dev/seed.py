from __future__ import annotations

from django.core.management import call_command


LEGACY_DEV_PROFILE = "e2e"


def run_dev_seed(*, reset: bool = False, export_path: str | None = None, **_: object) -> None:
    call_command(
        "seed_test_data",
        profile=LEGACY_DEV_PROFILE,
        reset=reset,
        export_fixtures=export_path,
    )