"""Tests for the anonymous cart cleanup scheduled job.

Covers:
- Settings defaults are sensible and settings values are forwarded correctly.
- Schedule registration is idempotent (multiple calls never create duplicates).
- The registered schedule targets the correct job function and uses the
  cron expression from settings.
- The job function reads ANONYMOUS_CART_TTL_DAYS from settings at call time.
"""

from unittest.mock import call, patch

import pytest
from django_q.models import Schedule

from carts.jobs import run_anonymous_cart_cleanup
from carts.schedules import (
    ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME,
    register_anonymous_cart_cleanup,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_default_ttl_days(settings):
    """ANONYMOUS_CART_TTL_DAYS defaults to 7."""
    # Remove any override so we fall back to the base default.
    settings.ANONYMOUS_CART_TTL_DAYS = 7
    assert settings.ANONYMOUS_CART_TTL_DAYS == 7


def test_default_cleanup_cron(settings):
    """ANONYMOUS_CART_CLEANUP_CRON defaults to daily at 03:00 UTC."""
    settings.ANONYMOUS_CART_CLEANUP_CRON = "0 3 * * *"
    assert settings.ANONYMOUS_CART_CLEANUP_CRON == "0 3 * * *"


# ---------------------------------------------------------------------------
# Schedule registration — correctness
# ---------------------------------------------------------------------------


def test_register_creates_schedule():
    """register_anonymous_cart_cleanup creates a Schedule row on first call."""
    assert not Schedule.objects.filter(
        name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME
    ).exists()

    register_anonymous_cart_cleanup()

    assert Schedule.objects.filter(
        name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME
    ).count() == 1


def test_registered_schedule_has_correct_func():
    """The schedule targets the carts.jobs.run_anonymous_cart_cleanup job."""
    register_anonymous_cart_cleanup()

    schedule = Schedule.objects.get(name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME)
    assert schedule.func == "carts.jobs.run_anonymous_cart_cleanup"


def test_registered_schedule_is_cron_type():
    """The schedule uses CRON schedule type."""
    register_anonymous_cart_cleanup()

    schedule = Schedule.objects.get(name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME)
    assert schedule.schedule_type == Schedule.CRON


def test_registered_schedule_repeats_indefinitely():
    """The schedule is set to repeat indefinitely (repeats=-1)."""
    register_anonymous_cart_cleanup()

    schedule = Schedule.objects.get(name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME)
    assert schedule.repeats == -1


def test_registered_schedule_uses_cron_from_settings(settings):
    """The schedule cron expression reflects ANONYMOUS_CART_CLEANUP_CRON."""
    settings.ANONYMOUS_CART_CLEANUP_CRON = "30 4 * * 0"  # non-default value

    register_anonymous_cart_cleanup()

    schedule = Schedule.objects.get(name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME)
    assert schedule.cron == "30 4 * * 0"


# ---------------------------------------------------------------------------
# Schedule registration — idempotency
# ---------------------------------------------------------------------------


def test_register_is_idempotent():
    """Calling register twice does not create duplicate schedule rows."""
    register_anonymous_cart_cleanup()
    register_anonymous_cart_cleanup()

    count = Schedule.objects.filter(
        name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME
    ).count()
    assert count == 1


def test_register_updates_cron_on_second_call(settings):
    """A second registration with a different cron updates the existing row."""
    settings.ANONYMOUS_CART_CLEANUP_CRON = "0 2 * * *"
    register_anonymous_cart_cleanup()

    settings.ANONYMOUS_CART_CLEANUP_CRON = "0 5 * * *"
    register_anonymous_cart_cleanup()

    schedule = Schedule.objects.get(name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME)
    assert schedule.cron == "0 5 * * *"
    assert Schedule.objects.filter(
        name=ANONYMOUS_CART_CLEANUP_SCHEDULE_NAME
    ).count() == 1


# ---------------------------------------------------------------------------
# Job function — settings forwarding
# ---------------------------------------------------------------------------


def test_job_calls_management_command_with_ttl_from_settings(settings):
    """run_anonymous_cart_cleanup passes ANONYMOUS_CART_TTL_DAYS to the command."""
    settings.ANONYMOUS_CART_TTL_DAYS = 14

    with patch("carts.jobs.call_command") as mock_call:
        run_anonymous_cart_cleanup()

    mock_call.assert_called_once_with("cleanup_anonymous_carts", days=14)


def test_job_uses_default_ttl_when_setting_absent(settings):
    """run_anonymous_cart_cleanup falls back to 7 when setting is missing."""
    # Simulate the setting being absent.
    if hasattr(settings, "ANONYMOUS_CART_TTL_DAYS"):
        delattr(settings, "ANONYMOUS_CART_TTL_DAYS")

    with patch("carts.jobs.call_command") as mock_call:
        run_anonymous_cart_cleanup()

    mock_call.assert_called_once_with("cleanup_anonymous_carts", days=7)
