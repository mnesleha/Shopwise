from django.conf import settings
from django.core.mail import send_mail


class EmailService:
    @staticmethod
    def send_plain_text(*, to_email: str, subject: str, body: str) -> None:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
        )
