def render_email_verification(
    *, recipient_email: str, verification_url: str
) -> tuple[str, str]:
    subject = "Verify your email"
    body = (
        f"Hi {recipient_email},\n\n"
        f"Please verify your email by visiting:\n{verification_url}\n"
    )
    return subject, body


def render_guest_order_link(
    *, recipient_email: str, order_number: str, guest_order_url: str
) -> tuple[str, str]:
    subject = f"Your order {order_number}"
    body = (
        f"Hi {recipient_email},\n\n"
        f"View your guest order here:\n{guest_order_url}\n"
    )
    return subject, body
