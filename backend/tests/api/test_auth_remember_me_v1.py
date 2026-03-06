"""
Tests for the "Remember me" feature on the login endpoint.

Covered scenarios:
  A) remember_me=true produces a longer refresh-cookie Max-Age than remember_me=false.
  B) logout-all invalidates a remember-me refresh token:
     after logout-all, POST /auth/refresh/ with the old token must return 401.
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
LOGOUT_ALL_URL = "/api/v1/account/logout-all/"

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register(client: APIClient, email: str, password: str = "Passw0rd!123") -> None:
    resp = client.post(
        REGISTER_URL,
        {"email": email, "password": password, "first_name": "R", "last_name": "M"},
        format="json",
    )
    assert resp.status_code == 201, resp.content


def _login(client: APIClient, email: str, password: str = "Passw0rd!123", remember_me: bool = False):
    resp = client.post(
        LOGIN_URL,
        {"email": email, "password": password, "remember_me": remember_me},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    return resp


def _refresh_cookie_max_age(response) -> int:
    """Return the Max-Age of the refresh cookie from the response (as int seconds)."""
    cookie_name = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")
    return int(response.cookies[cookie_name]["max-age"])


# ---------------------------------------------------------------------------
# A) remember_me sets a longer refresh cookie TTL
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_remember_me_true_produces_longer_refresh_cookie_max_age():
    """
    Contract: remember_me=true must yield a strictly larger refresh-cookie
    Max-Age than remember_me=false.

    Test settings define:
      AUTH_REFRESH_TTL_SECONDS         = 3600  (standard)
      AUTH_REFRESH_TTL_REMEMBER_SECONDS = 7200  (remember-me)
    """
    client = APIClient()
    email = "remember_ttl@example.com"
    _register(client, email)

    # Login without remember_me
    r_standard = _login(client, email, remember_me=False)
    standard_max_age = _refresh_cookie_max_age(r_standard)

    # Login with remember_me
    r_remember = _login(client, email, remember_me=True)
    remember_max_age = _refresh_cookie_max_age(r_remember)

    assert remember_max_age > standard_max_age, (
        f"Expected remember-me Max-Age ({remember_max_age}s) > "
        f"standard Max-Age ({standard_max_age}s)"
    )


@pytest.mark.django_db
def test_remember_me_false_uses_standard_ttl():
    """
    Contract: remember_me=false (or omitted) sets Max-Age to
    AUTH_REFRESH_TTL_SECONDS from settings.
    """
    client = APIClient()
    email = "standard_ttl@example.com"
    _register(client, email)

    r = _login(client, email, remember_me=False)
    actual_max_age = _refresh_cookie_max_age(r)
    expected_ttl = int(getattr(settings, "AUTH_REFRESH_TTL_SECONDS", 7 * 24 * 3600))

    assert actual_max_age == expected_ttl, (
        f"Expected standard Max-Age={expected_ttl}s, got {actual_max_age}s"
    )


@pytest.mark.django_db
def test_remember_me_true_uses_remember_ttl():
    """
    Contract: remember_me=true sets Max-Age to
    AUTH_REFRESH_TTL_REMEMBER_SECONDS from settings.
    """
    client = APIClient()
    email = "remember_ttl2@example.com"
    _register(client, email)

    r = _login(client, email, remember_me=True)
    actual_max_age = _refresh_cookie_max_age(r)
    expected_ttl = int(getattr(settings, "AUTH_REFRESH_TTL_REMEMBER_SECONDS", 30 * 24 * 3600))

    assert actual_max_age == expected_ttl, (
        f"Expected remember-me Max-Age={expected_ttl}s, got {actual_max_age}s"
    )


@pytest.mark.django_db
def test_remember_me_field_is_optional_defaults_to_false():
    """
    Contract: omitting remember_me from the request is equivalent to
    remember_me=false — the endpoint still returns 200.
    """
    client = APIClient()
    email = "no_remember_field@example.com"
    _register(client, email)

    # Post without remember_me key at all
    resp = client.post(
        LOGIN_URL,
        {"email": email, "password": "Passw0rd!123"},
        format="json",
    )
    assert resp.status_code == 200

    standard_max_age = _refresh_cookie_max_age(resp)
    expected_ttl = int(getattr(settings, "AUTH_REFRESH_TTL_SECONDS", 7 * 24 * 3600))
    assert standard_max_age == expected_ttl


# ---------------------------------------------------------------------------
# B) logout-all invalidates remember-me refresh token
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_logout_all_invalidates_remember_me_refresh_token():
    """
    Contract (revocation of remember-me sessions):
    A) Login with remember_me=true to obtain a long-lived refresh token.
    B) Call logout-all (token_version is incremented).
    C) Attempt to use the OLD remember-me refresh token -> must return 401.

    This verifies that the tv (token_version) claim revocation mechanism
    works identically for standard and remember-me tokens.
    """
    client = APIClient()
    email = "remember_revoke@example.com"
    _register(client, email)

    # Login with remember_me=true
    r = _login(client, email, remember_me=True)
    tokens = r.json()
    old_refresh = tokens["refresh"]
    access = tokens["access"]

    # Confirm the cookie Max-Age is the remember-me TTL (sanity check).
    remember_max_age = _refresh_cookie_max_age(r)
    expected_ttl = int(getattr(settings, "AUTH_REFRESH_TTL_REMEMBER_SECONDS", 30 * 24 * 3600))
    assert remember_max_age == expected_ttl

    # Authenticate and call logout-all.
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    logout_resp = client.post(LOGOUT_ALL_URL)
    assert logout_resp.status_code == 204

    # A fresh client has no auth cookies — use the old refresh token via body.
    fresh_client = APIClient()
    refresh_resp = fresh_client.post(
        REFRESH_URL,
        {"refresh": old_refresh},
        format="json",
    )
    assert refresh_resp.status_code == 401, (
        f"Expected 401 after logout-all, got {refresh_resp.status_code}: "
        f"{refresh_resp.content}"
    )


@pytest.mark.django_db
def test_logout_all_allows_new_login_after_revocation():
    """
    Contract: after logout-all, the user can log in again with remember_me=true
    and obtain a fresh (valid) remember-me session.
    """
    client = APIClient()
    email = "remember_relogin@example.com"
    _register(client, email)

    # First login with remember_me
    r1 = _login(client, email, remember_me=True)
    access = r1.json()["access"]

    # Logout-all
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    logout_resp = client.post(LOGOUT_ALL_URL)
    assert logout_resp.status_code == 204

    # Re-login with remember_me — must succeed and return correct TTL.
    fresh_client = APIClient()
    r2 = _login(fresh_client, email, remember_me=True)
    assert r2.status_code == 200
    assert r2.json().get("access")

    new_max_age = _refresh_cookie_max_age(r2)
    expected_ttl = int(getattr(settings, "AUTH_REFRESH_TTL_REMEMBER_SECONDS", 30 * 24 * 3600))
    assert new_max_age == expected_ttl
