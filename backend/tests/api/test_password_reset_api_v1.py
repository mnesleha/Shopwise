import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.sqlite
class TestPasswordResetV1:
    REQUEST_URL = "/api/v1/auth/password-reset/request/"
    CONFIRM_URL = "/api/v1/auth/password-reset/confirm/"

    def _client(self) -> APIClient:
        return APIClient()

    def _create_user(self, email: str, password: str = "OldPassw0rd!123"):
        User = get_user_model()
        return User.objects.create_user(email=email, password=password)

    def test_request_returns_204_even_if_email_does_not_exist(self):
        c = self._client()
        r = c.post(self.REQUEST_URL, {"email": "doesnotexist@example.com"}, format="json")
        assert r.status_code == 204

    def test_request_returns_204_if_email_exists(self):
        _ = self._create_user("reset1@example.com")
        c = self._client()
        r = c.post(self.REQUEST_URL, {"email": "reset1@example.com"}, format="json")
        assert r.status_code == 204

    def test_confirm_rejects_invalid_token(self):
        c = self._client()
        r = c.post(
            self.CONFIRM_URL,
            {"token": "invalid", "new_password": "NewPassw0rd!123", "new_password_confirm": "NewPassw0rd!123"},
            format="json",
        )
        assert r.status_code in (400, 404)

    def test_confirm_requires_password_confirmation_match(self):
        from accounts.models import PasswordResetRequest  # must be created

        user = self._create_user("reset2@example.com")

        # Create request directly (service should support test-only raw token helper)
        req = PasswordResetRequest.create_for_user_for_tests(user=user)
        token = req.get_token_for_tests()

        c = self._client()
        r = c.post(
            self.CONFIRM_URL,
            {"token": token, "new_password": "NewPassw0rd!123", "new_password_confirm": "TypoPassw0rd!123"},
            format="json",
        )
        assert r.status_code == 400

    def test_confirm_changes_password_single_use_and_revokes_sessions(self):
        from accounts.models import PasswordResetRequest  # must be created

        User = get_user_model()
        user = self._create_user("reset3@example.com", password="OldPassw0rd!123")
        before_tv = getattr(user, "token_version", None)

        req = PasswordResetRequest.create_for_user_for_tests(user=user)
        token = req.get_token_for_tests()

        c = self._client()
        r = c.post(
            self.CONFIRM_URL,
            {"token": token, "new_password": "NewPassw0rd!123", "new_password_confirm": "NewPassw0rd!123"},
            format="json",
        )
        assert r.status_code in (200, 204), getattr(r, "data", None)

        user.refresh_from_db()
        assert user.check_password("NewPassw0rd!123")

        if before_tv is not None:
            assert user.token_version == before_tv + 1

        req.refresh_from_db()
        assert req.used_at is not None

        # token must be single-use
        r2 = c.post(
            self.CONFIRM_URL,
            {"token": token, "new_password": "AnotherPassw0rd!123", "new_password_confirm": "AnotherPassw0rd!123"},
            format="json",
        )
        assert r2.status_code in (400, 404, 409)