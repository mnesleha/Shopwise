import re

from notifications.renderers import (
    render_email_verification,
    render_guest_order_link,
)


def test_render_email_verification_contains_token_and_url():
    subject, body = render_email_verification(
        recipient_email="alice@example.com",
        verification_url="https://example.test/verify-email?token=abc123",
    )

    assert isinstance(subject, str) and subject.strip()
    assert isinstance(body, str) and body.strip()

    assert "Verify" in subject  # keep it intentionally loose
    assert "https://example.test/verify-email?token=abc123" in body


def test_render_guest_order_link_contains_url_and_order_number():
    subject, body = render_guest_order_link(
        recipient_email="guest@example.com",
        order_number="SW-10001",
        guest_order_url="https://example.test/orders/123?token=tok_456",
    )

    assert isinstance(subject, str) and subject.strip()
    assert isinstance(body, str) and body.strip()

    assert "SW-10001" in subject or "SW-10001" in body
    assert "https://example.test/orders/123?token=tok_456" in body

    # MVP sanity: token should be present in link (do not validate token format strictly here)
    assert re.search(r"token=", body)
