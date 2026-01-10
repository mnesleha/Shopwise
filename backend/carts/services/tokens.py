import secrets


def generate_cart_token() -> str:
    """
    Generate a cryptographically secure opaque token for anonymous cart identification.

    Notes:
    - The raw token is only returned to the client (cookie/header).
    - Only the SHA-256 hash of this token is stored in DB.
    - This function is intentionally isolated to allow deterministic patching in tests.
    """
    return secrets.token_urlsafe(32)
