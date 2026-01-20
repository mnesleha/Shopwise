import pytest
from django.core import mail

from notifications.email_service import EmailService


@pytest.mark.django_db
def test_email_service_sends_plain_text_email_via_locmem(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "no-reply@shopwise.test"

    EmailService.send_plain_text(
        to_email="bob@example.com",
        subject="Test subject",
        body="Hello from Shopwise",
    )

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["bob@example.com"]
    assert message.subject == "Test subject"
    assert "Hello from Shopwise" in message.body
    assert message.from_email == "no-reply@shopwise.test"
