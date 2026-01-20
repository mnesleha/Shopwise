from django.conf import settings
from django.core.mail import send_mail


class EmailService:
    @staticmethod
    def send_plain_text(*, to_email: str, subject: str, body: str) -> None:
        """
        Send a plain-text email using Django's configured email backend.

        Notes:
        - This is a thin wrapper and MAY raise exceptions from the underlying backend.
        - Best-effort / swallowing behavior is implemented at the job layer.
        """
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
