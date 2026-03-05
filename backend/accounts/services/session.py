"""
Session management service — global revocation helpers.

Public API:
  - logout_all_devices(user)   — atomically bumps token_version, invalidating
                                  all refresh tokens that carry a stale tv claim.
  - issue_refresh_token(user)  — creates a RefreshToken with the tv claim set to
                                  the current token_version, used at login / register.
"""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.db.models import F

logger = logging.getLogger(__name__)

User = get_user_model()


def logout_all_devices(user) -> None:
    """
    Invalidate all refresh tokens for *user* by incrementing token_version.

    Uses an atomic F() update to avoid race conditions.  After this call,
    any refresh token whose tv claim differs from the new token_version will
    be rejected by RefreshView.

    The in-memory user object is refreshed so callers see the updated value.
    """
    User.objects.filter(pk=user.pk).update(token_version=F("token_version") + 1)
    # Refresh the in-memory instance so subsequent reads are consistent.
    user.refresh_from_db(fields=["token_version"])


def issue_refresh_token(user):
    """
    Create a RefreshToken for *user* and embed the tv (token_version) claim in
    BOTH the refresh token and the nested access token.

    Embedding tv in the access token enables immediate revocation on every
    authenticated request (CookieJWTAuthentication rejects any access token
    whose tv claim differs from the current token_version).

    Returns a RefreshToken instance (call str() to serialise).
    """
    from rest_framework_simplejwt.tokens import RefreshToken  # local import avoids circular deps

    token = RefreshToken.for_user(user)
    # Embed in refresh token — validated by RefreshView._check_token_version.
    token["tv"] = user.token_version
    # Embed in access token — validated by CookieJWTAuthentication.get_user
    # on every authenticated request, enabling immediate cross-device revocation.
    token.access_token["tv"] = user.token_version
    return token
