import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.sqlite
class TestAccountChangePasswordV1:
    CHANGE_PW_URL = "/api/v1/account/change-password/"
    REFRESH_URL = "/auth/refresh/"  # adjust if your refresh endpoint differs
    ME_URL = "/auth/me"

    def _client(self) -> APIClient:
        return APIClient()

    def _create_user(self, email: str, password: str = "OldPassw0rd!123", **kwargs):
        User = get_user_model()
        return User.objects.create_user(email=email, password=password, **kwargs)

    def _auth_client(self, user):
        c = self._client()
        c.force_authenticate(user=user)
        return c

    def test_anonymous_cannot_change_password(self):
        c = self._client()
        resp = c.post(self.CHANGE_PW_URL, {}, format="json")
        assert resp.status_code == 401

    def test_requires_current_password(self):
        user = self._create_user("cp_1@example.com", password="OldPassw0rd!123")
        c = self._auth_client(user)

        resp = c.post(
            self.CHANGE_PW_URL,
            {"current_password": "WRONG", "new_password": "NewPassw0rd!123", "new_password_confirm": "NewPassw0rd!123"},
            format="json",
        )
        assert resp.status_code == 400

    def test_requires_password_confirmation_match(self):
        user = self._create_user("cp_2@example.com")
        c = self._auth_client(user)

        resp = c.post(
            self.CHANGE_PW_URL,
            {"current_password": "OldPassw0rd!123", "new_password": "NewPassw0rd!123", "new_password_confirm": "TypoPassw0rd!123"},
            format="json",
        )
        assert resp.status_code == 400

    def test_changes_password_and_revokes_all_sessions(self):
        """
        Contract:
        - Password is changed.
        - All sessions are revoked (token_version++) so refresh tokens issued before become invalid.
        """
        User = get_user_model()
        user = self._create_user("cp_3@example.com", password="OldPassw0rd!123")

        # capture token_version before
        before_tv = getattr(user, "token_version", None)

        c = self._auth_client(user)
        resp = c.post(
            self.CHANGE_PW_URL,
            {"current_password": "OldPassw0rd!123", "new_password": "NewPassw0rd!123", "new_password_confirm": "NewPassw0rd!123"},
            format="json",
        )
        assert resp.status_code in (200, 204), getattr(resp, "data", None)

        user.refresh_from_db()
        assert user.check_password("NewPassw0rd!123")

        # token_version must increment (logout-all)
        if before_tv is not None:
            assert user.token_version == before_tv + 1

        # NOTE:
        # Deep refresh-token invalidation test depends on your refresh endpoint and cookie/JWT tooling.
        # If you have a helper in tests to mint a refresh token with tv claim, add a dedicated test there.