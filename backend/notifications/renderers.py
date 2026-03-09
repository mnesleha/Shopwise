def render_email_verification(
    *, recipient_email: str, verification_url: str
) -> tuple[str, str]:
    """
    Render subject/body for an email verification message (plain-text MVP).

    Requirements:
    - Body MUST include the exact verification_url provided.
    """
    subject = "Verify your email"
    body = (
        f"Hi {recipient_email},\n\n"
        f"Please verify your email by visiting:\n{verification_url}\n"
    )
    return subject, body


def render_guest_order_link(
    *, recipient_email: str, order_number: str, guest_order_url: str
) -> tuple[str, str]:
    """
    Render subject/body for a guest order access link (plain-text MVP).

    Requirements:
    - Body MUST include the exact guest_order_url provided.
    """
    subject = f"Your order {order_number}"
    body = (
        f"Hi {recipient_email},\n\n"
        f"View your guest order here:\n{guest_order_url}\n"
    )
    return subject, body


def render_email_change_confirm(
    *, recipient_email: str, confirm_url: str
) -> tuple[str, str]:
    """
    Render subject/body for the email-change confirmation message (plain-text).

    Sent to the *new* email address.
    Requirements:
    - Body MUST include the exact confirm_url provided.
    """
    subject = "Confirm your email address change"
    body = (
        f"Hi {recipient_email},\n\n"
        "We received a request to change your login email address.\n"
        "Click the link below to confirm the change:\n\n"
        f"{confirm_url}\n\n"
        "This link expires in 60 minutes. If you did not request this change, "
        "please ignore this email.\n"
    )
    return subject, body


def render_email_change_cancel_notification(
    *, recipient_email: str, cancel_url: str
) -> tuple[str, str]:
    """
    Render subject/body for the email-change security notification (plain-text).

    Sent to the *old* email address with a one-click cancel link.
    Requirements:
    - Body MUST include the exact cancel_url provided.
    """
    subject = "Security notice: email change requested"
    body = (
        f"Hi {recipient_email},\n\n"
        "A request was submitted to change the login email address of your account.\n"
        "If this was you, no action is needed — the change will take effect after\n"
        "the new address is confirmed.\n\n"
        "If you did NOT request this, click the link below to cancel immediately:\n\n"
        f"{cancel_url}\n\n"
        "This cancel link expires in 60 minutes.\n"
    )
    return subject, body


def render_password_change_notification(*, recipient_email: str) -> tuple[str, str]:
    """
    Render subject/body for a security notification sent after a password change.

    Sent to the account email to alert the user of the change.
    No action URL is needed — the change is already applied.
    """
    subject = "Security notice: your password was changed"
    body = (
        f"Hi {recipient_email},\n\n"
        "Your account password was just changed.\n"
        "If this was you, no action is needed.\n\n"
        "If you did NOT make this change, please contact support immediately\n"
        "and consider resetting your password.\n"
    )
    return subject, body


def render_password_reset_email(*, recipient_email: str, reset_url: str) -> tuple[str, str]:
    """
    Render subject/body for a password-reset email (plain-text MVP).

    Requirements:
    - Body MUST include the exact reset_url provided.
    - Token expires in 60 minutes.
    """
    subject = "Reset your password"
    body = (
        f"Hi {recipient_email},\n\n"
        "We received a request to reset the password for your account.\n"
        "Click the link below to choose a new password:\n\n"
        f"{reset_url}\n\n"
        "This link is valid for 60 minutes and can only be used once.\n"
        "If you did not request a password reset, you can safely ignore this email.\n"
    )
    return subject, body


def render_order_system_cancelled_notification(
    *, recipient_email: str, order_id: int
) -> tuple[str, str]:
    """
    Render subject/body for a system-cancellation notification sent when an order
    is automatically cancelled because its inventory reservation expired without
    a completed payment.

    Parameters
    ----------
    recipient_email:
        The customer's email address (used for greeting only; the actual
        delivery address is set by the caller).
    order_id:
        The primary key of the cancelled Order row.
    """
    subject = f"Your order #{order_id} has been cancelled"
    body = (
        f"Hi {recipient_email},\n\n"
        f"We're writing to let you know that your order #{order_id} has been\n"
        "automatically cancelled because payment was not completed before the\n"
        "reservation expired.\n\n"
        "If you still want to place this order, please visit our store and\n"
        "add the items to your cart again.\n\n"
        "If you have any questions, please contact our support team.\n"
    )
    return subject, body
