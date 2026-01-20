from notifications.email_service import EmailService
from notifications.renderers import (
    render_email_verification,
    render_guest_order_link,
)


def send_email_verification(*, recipient_email: str, verification_url: str) -> None:
    subject, body = render_email_verification(
        recipient_email=recipient_email,
        verification_url=verification_url,
    )
    EmailService.send_plain_text(
        to_email=recipient_email,
        subject=subject,
        body=body,
    )


def send_guest_order_link(
    *, recipient_email: str, order_number: str, guest_order_url: str
) -> None:
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
