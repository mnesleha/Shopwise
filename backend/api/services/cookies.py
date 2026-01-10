from django.conf import settings


def cart_token_cookie_kwargs() -> dict:
    """
    Standard cookie keyword arguments used for the anonymous cart token (cart_token).

    Purpose:
    - Keep cookie attributes consistent across endpoints that set/clear the guest cart token.
    - Support a secure-by-default browser flow (HttpOnly + SameSite=Lax).

    Notes:
    - Secure is controlled by settings.CART_TOKEN_COOKIE_SECURE (defaults to False for local dev).
    """
    return {
        "httponly": True,
        "samesite": "Lax",
        "secure": getattr(settings, "CART_TOKEN_COOKIE_SECURE", False),
    }
