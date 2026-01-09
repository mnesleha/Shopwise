import hashlib
from typing import Optional

from carts.models import Cart


def extract_cart_token(request) -> Optional[str]:
    token = request.headers.get("X-Cart-Token")
    if token:
        return token
    return request.COOKIES.get("cart_token")


def hash_cart_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_active_anonymous_cart_by_token(token: str) -> Optional[Cart]:
    token_hash = hash_cart_token(token)
    return Cart.objects.filter(
        user__isnull=True,
        status=Cart.Status.ACTIVE,
        anonymous_token_hash=token_hash,
    ).first()
