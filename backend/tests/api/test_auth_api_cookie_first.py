import pytest
from rest_framework.test import APIClient
from django.conf import settings

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
ME_URL = "/api/v1/auth/me/"
REFRESH_URL = "/api/v1/auth/refresh/"

@pytest.mark.django_db
def test_refresh_rotates_refresh_and_old_refresh_is_rejected():
    """
    Contract (cookie-first):
    - /refresh rotates refresh token (when enabled) and sets new refresh cookie.
    - old refresh token becomes unusable (blacklisted) when BLACKLIST_AFTER_ROTATION=True.
    """
    client = APIClient()

    client.post(
        REGISTER_URL,
        {
            "email": "refresh@example.com",
            "password": "Passw0rd!123",
            "first_name": "R",
            "last_name": "T",
        },
        format="json",
    )

    login = client.post(
        LOGIN_URL,
        {"email": "refresh@example.com", "password": "Passw0rd!123"},
        format="json",
    )
    assert login.status_code == 200
    first_tokens = login.json()

    old_refresh = first_tokens["refresh"]

    refresh_cookie_name = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")

    # Put OLD refresh into cookie (browser-like)
    client.cookies[refresh_cookie_name] = old_refresh

    # First refresh (should rotate) - no body needed
    r1 = client.post(REFRESH_URL, {}, format="json")
    assert r1.status_code == 200
    tokens_2 = r1.json()
    assert "access" in tokens_2
    assert "refresh" in tokens_2
    assert tokens_2["refresh"] != old_refresh

    # Second refresh using OLD refresh should fail:
    # overwrite cookie back to OLD refresh
    client.cookies[refresh_cookie_name] = old_refresh
    r2 = client.post(REFRESH_URL, {}, format="json")
    assert r2.status_code in (400, 401)

    body = r2.json()
    assert body["code"] in ("VALIDATION_ERROR", "TOKEN_INVALID", "INVALID_TOKEN", "NOT_AUTHENTICATED")
    assert "message" in body