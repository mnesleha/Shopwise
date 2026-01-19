import hashlib
import secrets

from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from orders.models import Order


class GuestOrderAccessService:
    """
    Guest order access token service.

    - Issues a capability token for guest orders only (Order.user is NULL).
    - Stores only a SHA-256 hash of the token in DB (plaintext token is never persisted).
    - Validates token without leaking order existence (callers should return 404 on invalid).
    """

    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Hash the plaintext token using a server-side secret (pepper).

        We prefer a dedicated pepper (GUEST_ACCESS_TOKEN_PEPPER) to allow independent rotation.
        Fallback to Django SECRET_KEY for MVP compatibility.
        """
        pepper = getattr(settings, "GUEST_ACCESS_TOKEN_PEPPER", None) or getattr(
            settings, "SECRET_KEY", None
        )
        if not pepper:
            raise ImproperlyConfigured(
                "Missing SECRET_KEY / GUEST_ACCESS_TOKEN_PEPPER for guest token hashing."
            )

        return hashlib.sha256(f"{pepper}{token}".encode("utf-8")).hexdigest()

    @staticmethod
    def issue_token(*, order: Order) -> str:
        if order.user_id is not None:
            raise ValueError(
                "Guest order token can only be issued for guest orders.")

        token = secrets.token_urlsafe(32)
        token_hash = GuestOrderAccessService._hash_token(token)

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

        token_hash = GuestOrderAccessService._hash_token(token)

        if not secrets.compare_digest(order.guest_access_token_hash, token_hash):
            return None

        return order


def generate_guest_access_url(*, order: Order, token: str) -> str:
    # PUBLIC_BASE_URL may or may not include trailing slash -> normalize using urljoin.
    base = settings.PUBLIC_BASE_URL
    path = f"/api/v1/guest/orders/{order.id}/"
    query = urlencode({"token": token})
    return f"{urljoin(base.rstrip('/') + '/', path.lstrip('/'))}?{query}"
