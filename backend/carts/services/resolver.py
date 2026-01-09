import hashlib
from typing import Optional
from __future__ import annotations

from carts.models import Cart


def extract_cart_token(request) -> Optional[str]:
    """
    Extract guest cart token from the incoming request.

    Precedence:
    1) Header: X-Cart-Token
    2) Cookie: cart_token

    Returns:
        The raw token string, or None if not present.
    """

    token = request.headers.get("X-Cart-Token")
    if token:
        return token
    return request.COOKIES.get("cart_token")


def hash_cart_token(token: str) -> str:
    """
    Hash a guest cart token using SHA-256 and return a 64-char hex digest.
    """

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_active_anonymous_cart_by_token(token: str) -> Optional[Cart]:
    """
    Resolve an ACTIVE anonymous cart by raw token value.

    Looks up carts where:
    - user is NULL (anonymous)
    - status is ACTIVE
    - anonymous_token_hash matches SHA-256(token)

    Returns:
        Cart instance if found, otherwise None.
    """

    token_hash = hash_cart_token(token)
    return Cart.objects.filter(
        user__isnull=True,
        status=Cart.Status.ACTIVE,
        anonymous_token_hash=token_hash,
    ).first()
