"""
Tests for global session revocation (logout-all) and the token_version mechanism.

Covered scenarios:
  1. POST /api/v1/account/logout-all/ requires authentication.
  2. POST /api/v1/account/logout-all/ returns 204 and clears auth cookies.
  3. After logout-all, the old refresh token is rejected with 401.
  4. After logout-all, the old ACCESS token is rejected with 401 (immediate revocation).
  5. After logout-all, a fresh login issues valid new tokens.
  6. The tv claim is embedded in both refresh and access tokens issued at login.
  7. confirm-email-change increments token_version (revokes sessions).
  8. logout_all_devices() service helper atomically increments token_version.
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
LOGOUT_ALL_URL = "/api/v1/account/logout-all/"
ME_URL = "/api/v1/auth/me/"

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(email: str = "revoke@example.com", password: str = "Passw0rd!123"):
    """Register a new user, log in, and return (client, tokens_dict)."""
    client = APIClient()
    client.post(
        REGISTER_URL,
        {"email": email, "password": password, "first_name": "R", "last_name": "T"},
        format="json",
    )
    login = client.post(LOGIN_URL, {"email": email, "password": password}, format="json")
    assert login.status_code == 200
    return client, login.json()


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_logout_all_requires_authentication():
    """Unauthenticated requests to logout-all must return 401."""
    client = APIClient()
    resp = client.post(LOGOUT_ALL_URL)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Core contract: old refresh token is rejected after logout-all
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_logout_all_revokes_old_refresh_token():
    """
    Contract (revocation mechanism):
    A) Login to obtain access + refresh tokens.
    B) Call logout-all (token_version is incremented).
    C) Attempt to use the OLD refresh token -> must return 401.
    """
    client, tokens = _register_and_login("revoke1@example.com")

    old_refresh = tokens["refresh"]
    access = tokens["access"]

    # Authenticate and call logout-all.
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp = client.post(LOGOUT_ALL_URL)
    assert resp.status_code == 204

    # Use old refresh token via the body (cookie is now cleared).
    anon_client = APIClient()
    refresh_resp = anon_client.post(REFRESH_URL, {"refresh": old_refresh}, format="json")

    # Must be rejected — session was revoked.
    assert refresh_resp.status_code in (400, 401), (
        f"Expected 400/401 after logout-all, got {refresh_resp.status_code}: {refresh_resp.json()}"
    )


@pytest.mark.django_db
def test_logout_all_via_cookie_revokes_old_refresh_token():
    """
    Same as above but exercises the cookie path: old refresh cookie is rejected.
    """
    client, tokens = _register_and_login("revoke2@example.com")

    access = tokens["access"]
    old_refresh = tokens["refresh"]
    refresh_cookie_name = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")

    # Authenticate and call logout-all.
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp = client.post(LOGOUT_ALL_URL)
    assert resp.status_code == 204

    # Place the old refresh token into a cookie and try to refresh.
    anon_client = APIClient()
    anon_client.cookies[refresh_cookie_name] = old_refresh
    refresh_resp = anon_client.post(REFRESH_URL, {}, format="json")

    assert refresh_resp.status_code in (400, 401), (
        f"Expected 400/401 after logout-all (cookie path), got {refresh_resp.status_code}"
    )


@pytest.mark.django_db
def test_logout_all_response_clears_auth_cookies():
    """logout-all must delete both auth cookies in the response."""
    client, tokens = _register_and_login("revoke3@example.com")

    access_cookie_name = getattr(settings, "AUTH_COOKIE_ACCESS", "access_token")
    refresh_cookie_name = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    resp = client.post(LOGOUT_ALL_URL)

    assert resp.status_code == 204
    # Deleted cookies are set to empty string with max_age=0 (or just absent).
    # DRF / Django test client represents deleted cookies as morsel with max_age 0.
    for cookie_name in (access_cookie_name, refresh_cookie_name):
        morsel = resp.cookies.get(cookie_name)
        if morsel:
            # If the cookie is present in the response it must be cleared.
            assert morsel["max-age"] in (0, "0", "") or morsel.value == "", (
                f"Cookie {cookie_name!r} was not cleared in the response"
            )


# ---------------------------------------------------------------------------
# Post-revocation: re-login must issue valid tokens
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_fresh_login_after_logout_all_issues_valid_tokens():
    """After logout-all, a new login must work and the new refresh token must be usable."""
    email = "revoke4@example.com"
    password = "Passw0rd!123"
    client, tokens = _register_and_login(email, password)

    # Revoke all sessions.
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.post(LOGOUT_ALL_URL).status_code == 204

    # Re-login.
    new_login = client.post(LOGIN_URL, {"email": email, "password": password}, format="json")
    assert new_login.status_code == 200
    new_tokens = new_login.json()

    # New refresh token must be usable.
    anon_client = APIClient()
    refresh_resp = anon_client.post(REFRESH_URL, {"refresh": new_tokens["refresh"]}, format="json")
    assert refresh_resp.status_code == 200, (
        f"New refresh token was rejected after re-login: {refresh_resp.json()}"
    )


@pytest.mark.django_db
def test_logout_all_revokes_access_token_immediately():
    """
    Critical regression test: after logout-all the OLD access token must be
    rejected on the VERY NEXT authenticated request (not just at refresh time).

    This covers the cross-device scenario:
      1. Device A and Device B are both logged in.
      2. Device A calls logout-all (token_version++).
      3. Device B immediately makes a request with its still-valid access token
         -> must receive 401, NOT 200.
    """
    client, tokens = _register_and_login("revoke_access@example.com")
    old_access = tokens["access"]

    # Revoke all sessions.
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
    assert client.post(LOGOUT_ALL_URL).status_code == 204

    # Simulate a different device using the old access token.
    other_device = APIClient()
    other_device.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")

    # /api/v1/account/ is IsAuthenticated — must reject the stale access token.
    account_resp = other_device.get("/api/v1/account/")
    assert account_resp.status_code == 401, (
        f"Stale access token was accepted after logout-all, got {account_resp.status_code}: "
        f"{account_resp.json()}"
    )


@pytest.mark.django_db
def test_confirm_email_change_old_access_token_is_rejected(settings):
    """
    End-to-end: after confirm_email_change, the pre-change ACCESS token from
    another device must be rejected immediately (not just at refresh time).
    This covers the exact reported bug scenario.
    """
    settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS = True

    from accounts.services.email_change import request_email_change, confirm_email_change
    from accounts.models import EmailChangeRequest

    email = "ecv_access_e2e@example.com"
    password = "Passw0rd!123"

    # Simulate "device B" login -> gets an access token.
    _client, tokens = _register_and_login(email, password)
    old_access = tokens["access"]

    user = User.objects.get(email=email)

    # Simulate email change from "device A".
    request_email_change(
        user,
        new_email="ecv_access_e2e_new@example.com",
        current_password=password,
    )
    ecr = EmailChangeRequest.objects.get(user=user)
    confirm_email_change(ecr._confirm_token_debug)

    # Device B tries to use its old access token on any authenticated endpoint.
    other_device = APIClient()
    other_device.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
    resp = other_device.get("/api/v1/account/")
    assert resp.status_code == 401, (
        f"Pre-change access token should be immediately rejected after email change, "
        f"got {resp.status_code}: {resp.json()}"
    )


# ---------------------------------------------------------------------------
# tv claim in issued tokens
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_embeds_tv_claim_in_refresh_and_access_token():
    """
    Both the refresh token and the access token issued at login must carry
    the tv claim matching the user's token_version.
    """
    import jwt as pyjwt  # PyJWT is a transitive dep of djangorestframework-simplejwt

    email = "tv_claim@example.com"
    client, tokens = _register_and_login(email)

    user = User.objects.get(email=email)

    for token_type, token_str in (("refresh", tokens["refresh"]), ("access", tokens["access"])):
        decoded = pyjwt.decode(token_str, options={"verify_signature": False})
        assert "tv" in decoded, f"{token_type} token must contain the 'tv' claim"
        assert decoded["tv"] == user.token_version, (
            f"{token_type} token tv claim {decoded['tv']} != user.token_version {user.token_version}"
        )


# ---------------------------------------------------------------------------
# logout_all_devices service helper
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_logout_all_devices_increments_token_version():
    """logout_all_devices() must atomically increment user.token_version."""
    from accounts.services.session import logout_all_devices

    user = User.objects.create_user(
        email="svc_revoke@example.com", password="Passw0rd!123"
    )
    assert user.token_version == 1

    logout_all_devices(user)
    assert user.token_version == 2  # in-memory refreshed

    # Verify DB value.
    user.refresh_from_db()
    assert user.token_version == 2


@pytest.mark.django_db
def test_logout_all_devices_called_twice_increments_twice():
    """Each logout_all_devices() call must increment independently."""
    from accounts.services.session import logout_all_devices

    user = User.objects.create_user(
        email="svc_revoke2@example.com", password="Passw0rd!123"
    )
    logout_all_devices(user)
    logout_all_devices(user)

    user.refresh_from_db()
    assert user.token_version == 3


# ---------------------------------------------------------------------------
# confirm-email-change increments token_version
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.usefixtures("settings")
def test_confirm_email_change_increments_token_version(settings):
    """
    After confirm_email_change succeeds, the user's token_version must be
    greater than before, invalidating all previously issued refresh tokens.
    """
    settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS = True

    from accounts.services.email_change import request_email_change, confirm_email_change
    from accounts.models import EmailChangeRequest

    user = User.objects.create_user(
        email="ecv@example.com", password="Passw0rd!123"
    )
    initial_version = user.token_version

    request_email_change(
        user,
        new_email="ecv_new@example.com",
        current_password="Passw0rd!123",
    )

    ecr = EmailChangeRequest.objects.get(user=user)
    # Access raw token stored in debug mode.
    raw_token = ecr._confirm_token_debug

    confirm_email_change(raw_token)

    user.refresh_from_db()
    assert user.token_version > initial_version, (
        "token_version must be incremented after confirm_email_change"
    )


@pytest.mark.django_db
def test_confirm_email_change_old_refresh_token_is_rejected(settings):
    """
    End-to-end: after confirm_email_change, the user's pre-change refresh
    token must be rejected by RefreshView (401/400).
    """
    settings.STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS = True

    from accounts.services.email_change import request_email_change, confirm_email_change
    from accounts.models import EmailChangeRequest

    email = "ecv_e2e@example.com"
    password = "Passw0rd!123"

    # Login to get a refresh token BEFORE the email change.
    client, tokens = _register_and_login(email, password)
    old_refresh = tokens["refresh"]

    user = User.objects.get(email=email)

    request_email_change(
        user,
        new_email="ecv_e2e_new@example.com",
        current_password=password,
    )

    ecr = EmailChangeRequest.objects.get(user=user)
    raw_token = ecr._confirm_token_debug
    confirm_email_change(raw_token)

    # Old refresh token must now be rejected.
    anon_client = APIClient()
    refresh_resp = anon_client.post(REFRESH_URL, {"refresh": old_refresh}, format="json")
    assert refresh_resp.status_code in (400, 401), (
        f"Pre-change refresh token should be rejected after email change, "
        f"got {refresh_resp.status_code}: {refresh_resp.json()}"
    )
