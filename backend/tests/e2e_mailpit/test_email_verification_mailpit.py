import pytest
from django.core import mail

from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import send_mail
from unittest.mock import patch

from tests.e2e_mailpit.mailpit_client import MailpitClient


@pytest.mark.e2e_mailpit
@pytest.mark.django_db
def test_verification_email_is_delivered_to_mailpit(client, settings, django_user_model, monkeypatch):
    settings.PUBLIC_BASE_URL = "https://example.test"
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "127.0.0.1"
    settings.EMAIL_PORT = 1025
    settings.DEFAULT_FROM_EMAIL = "no-reply@shopwise.test"
    settings.Q_CLUSTER = {**getattr(settings, "Q_CLUSTER", {}), "sync": True}

    mailpit = MailpitClient("http://127.0.0.1:8025")

    django_user_model.objects.create_user(
        email="u2@example.com", password="pw")

    # 1) capture on_commit
    from django.db import transaction
    callbacks = []
    monkeypatch.setattr(transaction, "on_commit", lambda fn,
                        using=None: callbacks.append(fn))

    resp = client.post(
        "/api/v1/auth/request-email-verification/",
        data={"email": "u2@example.com"},
        content_type="application/json",
    )
    assert resp.status_code in (200, 202)
    assert len(
        callbacks) == 1, f"Expected 1 on_commit callback, got {len(callbacks)}"

    # 2) ensure SMTP backend is actually used (pickling-safe)
    with patch("notifications.email_service.send_mail", wraps=send_mail) as send_mail_mock:
        callbacks[0]()
        assert send_mail_mock.called, "Expected django.core.mail.send_mail to be called"

    # 3) now wait for the actual email
    msg_meta = mailpit.wait_for_message_containing("u2@example.com")
    msg = mailpit.get_message(msg_meta["ID"])
    raw = str(msg)
    assert "u2@example.com" in raw
    assert "token=" in raw
    assert "https://example.test" in raw
