"""Django-Q2 job definitions for the carts app.

Each function here is a thin adapter that reads runtime configuration from
settings and delegates all business logic to the existing management command.
This keeps the management command as the single source of truth.
"""

from django.conf import settings
from django.core.management import call_command


def run_anonymous_cart_cleanup() -> None:
    """Execute the anonymous cart cleanup management command.

    Reads ``ANONYMOUS_CART_TTL_DAYS`` from settings at call time so that
    changing the setting takes effect on the next run without needing to
    re-register the schedule.

    Intended to be invoked by the django-q2 scheduler; can also be called
    directly in tests or from the REPL.
    """
    days: int = getattr(settings, "ANONYMOUS_CART_TTL_DAYS", 7)
    call_command("cleanup_anonymous_carts", days=days)
