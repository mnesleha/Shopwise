from unittest.mock import patch

from notifications import jobs


def test_job_send_email_verification_calls_email_service():
    with patch("notifications.jobs.EmailService.send_plain_text") as send_mock:
        jobs.send_email_verification(
            recipient_email="alice@example.com",
            verification_url="https://example.test/verify-email?token=abc123",
        )

    assert send_mock.call_count == 1
    _, kwargs = send_mock.call_args
    assert kwargs["to_email"] == "alice@example.com"
    assert "https://example.test/verify-email?token=abc123" in kwargs["body"]


def test_job_send_guest_order_link_calls_email_service():
    with patch("notifications.jobs.EmailService.send_plain_text") as send_mock:
        jobs.send_guest_order_link(
            recipient_email="guest@example.com",
            order_number="SW-10001",
            guest_order_url="https://example.test/orders/123?token=tok_456",
        )

    assert send_mock.call_count == 1
    _, kwargs = send_mock.call_args
    assert kwargs["to_email"] == "guest@example.com"
    assert "SW-10001" in kwargs["subject"] or "SW-10001" in kwargs["body"]
    assert "https://example.test/orders/123?token=tok_456" in kwargs["body"]
