"""
Django-Q2 job entrypoints for notification delivery.

These functions represent the boundary between business logic and
best-effort side effects. They MUST NOT raise exceptions that could
break request flows or background workers.
"""

from notifications.email_service import EmailService
from notifications.renderers import (
    render_email_change_cancel_notification,
    render_email_change_confirm,
    render_email_verification,
    render_guest_order_link,
    render_order_system_cancelled_notification,
    render_password_change_notification,
    render_password_reset_email,
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


def send_email_change_confirm(*, recipient_email: str, confirm_url: str) -> None:
    """
    Send an email-change confirmation message to the *new* email address.

    Best-effort semantics:
    - Failures MUST NOT propagate.
    - Errors are delegated to NotificationErrorHandler.
    """
    try:
        subject, body = render_email_change_confirm(
            recipient_email=recipient_email,
            confirm_url=confirm_url,
        )
        EmailService.send_plain_text(
            to_email=recipient_email,
            subject=subject,
            body=body,
        )
    except Exception:
        NotificationErrorHandler.handle(
            NotificationSendError(
                code="EMAIL_CHANGE_CONFIRM_SEND_FAILED",
                message="Failed to send email-change confirmation email.",
                context={
                    "recipient_email": recipient_email,
                    "confirm_url": confirm_url,
                },
            )
        )


def send_email_change_cancel_notification(
    *, recipient_email: str, cancel_url: str
) -> None:
    """
    Send a security notification to the *old* email address with a cancel link.

    Best-effort semantics:
    - Failures MUST NOT propagate.
    - Errors are delegated to NotificationErrorHandler.
    """
    try:
        subject, body = render_email_change_cancel_notification(
            recipient_email=recipient_email,
            cancel_url=cancel_url,
        )
        EmailService.send_plain_text(
            to_email=recipient_email,
            subject=subject,
            body=body,
        )
    except Exception:
        NotificationErrorHandler.handle(
            NotificationSendError(
                code="EMAIL_CHANGE_CANCEL_NOTIFY_SEND_FAILED",
                message="Failed to send email-change cancellation notification.",
                context={
                    "recipient_email": recipient_email,
                    "cancel_url": cancel_url,
                },
            )
        )

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


def send_password_reset_email(*, recipient_email: str, reset_url: str) -> None:
    """
    Send a password-reset email to the user.

    Best-effort semantics:
    - Failures MUST NOT propagate.
    - Errors are delegated to NotificationErrorHandler.
    """
    try:
        subject, body = render_password_reset_email(
            recipient_email=recipient_email,
            reset_url=reset_url,
        )
        EmailService.send_plain_text(
            to_email=recipient_email,
            subject=subject,
            body=body,
        )
    except Exception:
        NotificationErrorHandler.handle(
            NotificationSendError(
                code="PASSWORD_RESET_EMAIL_SEND_FAILED",
                message="Failed to send password-reset email.",
                context={"recipient_email": recipient_email, "reset_url": reset_url},
            )
        )
        return


def send_password_change_notification(*, recipient_email: str) -> None:
    """
    Send a security notification after a successful password change.

    Best-effort semantics:
    - Failures MUST NOT propagate.
    - Errors are delegated to NotificationErrorHandler.
    """
    try:
        subject, body = render_password_change_notification(
            recipient_email=recipient_email,
        )
        EmailService.send_plain_text(
            to_email=recipient_email,
            subject=subject,
            body=body,
        )
    except Exception:
        NotificationErrorHandler.handle(
            NotificationSendError(
                code="PASSWORD_CHANGE_NOTIFY_SEND_FAILED",
                message="Failed to send password-change security notification.",
                context={"recipient_email": recipient_email},
            )
        )
        return


def send_order_system_cancelled_notification(
    *, recipient_email: str, order_id: int
) -> None:
    """Send a cancellation notice when an order is system-cancelled due to
    an expired inventory reservation / unpaid payment.

    Best-effort semantics:
    - Failures MUST NOT propagate.
    - Errors are delegated to NotificationErrorHandler.
    """
    try:
        subject, body = render_order_system_cancelled_notification(
            recipient_email=recipient_email,
            order_id=order_id,
        )
        EmailService.send_plain_text(
            to_email=recipient_email,
            subject=subject,
            body=body,
        )
    except Exception:
        NotificationErrorHandler.handle(
            NotificationSendError(
                code="ORDER_SYSTEM_CANCELLED_NOTIFY_SEND_FAILED",
                message="Failed to send order system-cancellation notification.",
                context={"recipient_email": recipient_email, "order_id": order_id},
            )
        )
