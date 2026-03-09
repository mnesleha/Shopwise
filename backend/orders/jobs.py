"""Django-Q2 job definitions for the orders app.

Each function is a thin adapter that delegates to the existing management
command.  All business logic lives in the management command / service layer,
not here.
"""

from django.core.management import call_command


def run_overdue_reservation_expiration() -> None:
    """Execute the overdue reservation expiration management command.

    Calls ``expire_overdue_reservations`` without ``--as-of``, so the command
    uses the current wall-clock time.  On each run the service:

    * Marks ACTIVE reservations past their TTL as EXPIRED.
    * Cancels the parent order (status=CANCELLED, cancelled_by=SYSTEM,
      cancel_reason=PAYMENT_EXPIRED).
    * Emits audit events for both the reservation batch and the order, giving
      a traceable hook for future notification policies.

    Intended to be invoked by the django-q2 scheduler; safe to call directly
    in tests or from the REPL.
    """
    call_command("expire_overdue_reservations")
