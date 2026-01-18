import hashlib
import secrets

from django.conf import settings
from django.utils import timezone

from orders.models import Order


class GuestOrderAccessService:
    @staticmethod
    def issue_token(*, order: Order) -> str:
        if order.user_id is not None:
            raise ValueError("Guest order token can only be issued for guest orders.")

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(
            f"{settings.SECRET_KEY}{token}".encode("utf-8")
        ).hexdigest()

        order.guest_access_token_hash = token_hash
        order.guest_access_token_created_at = timezone.now()
        order.save(
            update_fields=[
                "guest_access_token_hash",
                "guest_access_token_created_at",
            ]
        )
        return token

    @staticmethod
    def validate(*, order_id: int, token: str) -> Order | None:
        if not token:
            return None

        order = Order.objects.filter(id=order_id).first()
        if not order or order.user_id is not None:
            return None

        if not order.guest_access_token_hash:
            return None

        token_hash = hashlib.sha256(
            f"{settings.SECRET_KEY}{token}".encode("utf-8")
        ).hexdigest()

        if not secrets.compare_digest(order.guest_access_token_hash, token_hash):
            return None

        return order


def generate_guest_access_url(*, order: Order, token: str) -> str:
    return f"{settings.PUBLIC_BASE_URL}/api/v1/guest/orders/{order.id}/?token={token}"
