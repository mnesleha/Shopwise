"""
Django-Q2 job entrypoints for notification delivery.

These functions represent the boundary between business logic and
best-effort side effects. They MUST NOT raise exceptions that could
break request flows or background workers.
"""

from notifications.email_service import EmailService
from notifications.renderers import (
    render_email_verification,
    render_guest_order_link,
)
from notifications.exceptions import NotificationSendError
from notifications.error_handler import NotificationErrorHandler


def send_email_verification(*, recipient_email: str, verification_url: str) -> None:
    """
    Send an email verification message.

    Best-effort semantics:
    - Failures MUST NOT propagate.
    - Errors are delegated to NotificationErrorHandler.
    """
    try:
        subject, body = render_email_verification(
            recipient_email=recipient_email,
            verification_url=verification_url,
        )
        EmailService.send_plain_text(
            to_email=recipient_email,
            subject=subject,
            body=body,
        )

    except Exception as exc:
        NotificationErrorHandler.handle(
            NotificationSendError(
                code="EMAIL_VERIFICATION_SEND_FAILED",
                message="Failed to send email verification notification.",
                context={
                    "recipient_email": recipient_email,
                    "verification_url": verification_url,
                },
            )
        )
        return


def send_guest_order_link(
    *, recipient_email: str, order_number: str, guest_order_url: str
) -> None:
    """
    Send a guest order access link email.

    Best-effort semantics:
    - Failures MUST NOT propagate.
    - Errors are delegated to NotificationErrorHandler.
    """
    try:
        subject, body = render_guest_order_link(
            recipient_email=recipient_email,
            order_number=order_number,
            guest_order_url=guest_order_url,
        )
        EmailService.send_plain_text(
            to_email=recipient_email,
            subject=subject,
            body=body,
        )

    except Exception as exc:
        NotificationErrorHandler.handle(
            NotificationSendError(
                code="GUEST_ORDER_EMAIL_SEND_FAILED",
                message="Failed to send guest order access link email.",
                context={
                    "recipient_email": recipient_email,
                    "order_number": order_number,
                    "guest_order_url": guest_order_url,
                },
            )
        )
        return
