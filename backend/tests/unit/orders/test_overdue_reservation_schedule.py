"""Tests for the overdue reservation expiration scheduled job.

Covers:
- Settings default is a sensible cron expression.
- Schedule registration is idempotent.
- The registered schedule targets the correct job function and cron.
- The job function delegates to the management command (no duplicated logic).
- sync_q_schedules management command registers both schedules in one call.

Domain behavior (expire_overdue_reservations) is tested in the existing
test_reservation_expiry_dry_run_count.py and related unit tests.  This file
intentionally does NOT re-test the service layer.
"""

from unittest.mock import patch, call

import pytest
from django_q.models import Schedule

from orders.jobs import run_overdue_reservation_expiration
from orders.schedules import (
    OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME,
    register_overdue_reservation_expiration,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_default_overdue_cleanup_cron(settings):
    """OVERDUE_RESERVATIONS_CLEANUP_CRON has a sensible non-empty default."""
    settings.OVERDUE_RESERVATIONS_CLEANUP_CRON = "*/15 * * * *"
    assert settings.OVERDUE_RESERVATIONS_CLEANUP_CRON == "*/15 * * * *"


# ---------------------------------------------------------------------------
# Schedule registration — correctness
# ---------------------------------------------------------------------------


def test_register_creates_schedule():
    """register_overdue_reservation_expiration creates a Schedule row on first call."""
    assert not Schedule.objects.filter(
        name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME
    ).exists()

    register_overdue_reservation_expiration()

    assert Schedule.objects.filter(
        name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME
    ).count() == 1


def test_registered_schedule_has_correct_func():
    """The schedule targets orders.jobs.run_overdue_reservation_expiration."""
    register_overdue_reservation_expiration()

    schedule = Schedule.objects.get(name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME)
    assert schedule.func == "orders.jobs.run_overdue_reservation_expiration"


def test_registered_schedule_is_cron_type():
    """The schedule uses CRON schedule type."""
    register_overdue_reservation_expiration()

    schedule = Schedule.objects.get(name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME)
    assert schedule.schedule_type == Schedule.CRON


def test_registered_schedule_repeats_indefinitely():
    """The schedule is set to repeat indefinitely (repeats=-1)."""
    register_overdue_reservation_expiration()

    schedule = Schedule.objects.get(name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME)
    assert schedule.repeats == -1


def test_registered_schedule_uses_cron_from_settings(settings):
    """The schedule cron expression reflects OVERDUE_RESERVATIONS_CLEANUP_CRON."""
    settings.OVERDUE_RESERVATIONS_CLEANUP_CRON = "0 * * * *"  # hourly

    register_overdue_reservation_expiration()

    schedule = Schedule.objects.get(name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME)
    assert schedule.cron == "0 * * * *"


# ---------------------------------------------------------------------------
# Schedule registration — idempotency
# ---------------------------------------------------------------------------


def test_register_is_idempotent():
    """Calling register twice does not create duplicate schedule rows."""
    register_overdue_reservation_expiration()
    register_overdue_reservation_expiration()

    count = Schedule.objects.filter(
        name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME
    ).count()
    assert count == 1


def test_register_updates_cron_on_second_call(settings):
    """A second registration with a changed cron updates the existing row."""
    settings.OVERDUE_RESERVATIONS_CLEANUP_CRON = "*/10 * * * *"
    register_overdue_reservation_expiration()

    settings.OVERDUE_RESERVATIONS_CLEANUP_CRON = "*/30 * * * *"
    register_overdue_reservation_expiration()

    schedule = Schedule.objects.get(name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME)
    assert schedule.cron == "*/30 * * * *"
    assert Schedule.objects.filter(
        name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME
    ).count() == 1


# ---------------------------------------------------------------------------
# Job function — delegates to management command
# ---------------------------------------------------------------------------


def test_job_calls_management_command():
    """run_overdue_reservation_expiration delegates to the management command."""
    with patch("orders.jobs.call_command") as mock_call:
        run_overdue_reservation_expiration()

    mock_call.assert_called_once_with("expire_overdue_reservations")


def test_job_does_not_pass_extra_args():
    """The job calls the command with no positional/keyword overrides.

    The command defaults to timezone.now() for --as-of and omits --dry-run,
    so the job must not inject those values — the scheduled job is always
    a real run at the current time.
    """
    with patch("orders.jobs.call_command") as mock_call:
        run_overdue_reservation_expiration()

    args, kwargs = mock_call.call_args
    assert args == ("expire_overdue_reservations",)
    assert kwargs == {}


# ---------------------------------------------------------------------------
# sync_q_schedules management command — registers both schedules
# ---------------------------------------------------------------------------


def test_sync_q_schedules_registers_both_jobs():
    """python manage.py sync_q_schedules creates both schedule rows."""
    from django.core.management import call_command as django_call_command

    django_call_command("sync_q_schedules", verbosity=0)

    from carts.schedules import ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME

    assert Schedule.objects.filter(
        name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME
    ).exists(), "anonymous cart cleanup schedule missing"

    assert Schedule.objects.filter(
        name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME
    ).exists(), "overdue reservation expiration schedule missing"


def test_sync_q_schedules_is_idempotent():
    """Running sync_q_schedules twice does not create duplicates."""
    from django.core.management import call_command as django_call_command
    from carts.schedules import ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME

    django_call_command("sync_q_schedules", verbosity=0)
    django_call_command("sync_q_schedules", verbosity=0)

    assert Schedule.objects.filter(
        name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME
    ).count() == 1
    assert Schedule.objects.filter(
        name=OVERDUE_RESERVATION_EXPIRATION_SCHEDULE_NAME
    ).count() == 1
