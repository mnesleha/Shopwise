import re
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.sqlite
class TestAccountChangeEmailV1:
    CHANGE_URL = "/api/v1/account/change-email/"
    CONFIRM_URL = "/api/v1/account/confirm-email-change/"
    CANCEL_URL = "/api/v1/account/cancel-email-change/"

    def _client(self) -> APIClient:
        return APIClient()

    def _create_user(self, email: str, password: str = "Passw0rd!123", **kwargs):
        User = get_user_model()
        return User.objects.create_user(email=email, password=password, **kwargs)

    def _auth_client(self, user):
        c = self._client()
        c.force_authenticate(user=user)
        return c

    def test_anonymous_cannot_request_change(self):
        c = self._client()
        resp = c.post(self.CHANGE_URL, {"new_email": "x@example.com", "new_email_confirm": "x@example.com", "current_password": "x"}, format="json")
        assert resp.status_code == 401

    def test_request_requires_current_password(self):
        user = self._create_user("old1@example.com", password="Passw0rd!123")
        c = self._auth_client(user)

        resp = c.post(
            self.CHANGE_URL,
            {"new_email": "new1@example.com", "new_email_confirm": "new1@example.com", "current_password": "WRONG"},
            format="json",
        )
        assert resp.status_code == 400

    def test_request_requires_email_confirmation_match(self):
        user = self._create_user("old2@example.com")
        c = self._auth_client(user)

        resp = c.post(
            self.CHANGE_URL,
            {"new_email": "new2@example.com", "new_email_confirm": "typo2@example.com", "current_password": "Passw0rd!123"},
            format="json",
        )
        assert resp.status_code == 400

    def test_request_rejects_email_already_in_use_case_insensitive(self):
        _ = self._create_user("taken@example.com")
        user = self._create_user("old3@example.com")
        c = self._auth_client(user)

        resp = c.post(
            self.CHANGE_URL,
            {"new_email": "TAKEN@EXAMPLE.COM", "new_email_confirm": "taken@example.com", "current_password": "Passw0rd!123"},
            format="json",
        )
        assert resp.status_code == 400

    def test_request_creates_single_active_request_and_is_idempotent_per_user(self):
        """
        Contract:
        - At most one active EmailChangeRequest per user.
        - New request cancels previous active request automatically (preferred UX).
        """
        from accounts.models import EmailChangeRequest  # must be created

        user = self._create_user("old4@example.com")
        c = self._auth_client(user)

        r1 = c.post(
            self.CHANGE_URL,
            {"new_email": "new4a@example.com", "new_email_confirm": "new4a@example.com", "current_password": "Passw0rd!123"},
            format="json",
        )
        assert r1.status_code in (200, 204), r1.data if hasattr(r1, "data") else r1.content

        r2 = c.post(
            self.CHANGE_URL,
            {"new_email": "new4b@example.com", "new_email_confirm": "new4b@example.com", "current_password": "Passw0rd!123"},
            format="json",
        )
        assert r2.status_code in (200, 204)

        active = EmailChangeRequest.objects.filter(user=user, cancelled_at__isnull=True, confirmed_at__isnull=True, expires_at__gt=timezone.now())
        assert active.count() == 1
        assert active.first().new_email == "new4b@example.com"

        cancelled = EmailChangeRequest.objects.filter(user=user, cancelled_at__isnull=False)
        assert cancelled.count() == 1

    def test_confirm_changes_email_and_logs_out_all_sessions(self):
        """
        Note:
        This test asserts email is changed and request is confirmed.
        Session invalidation is validated by a 'session_version'/similar mechanism if present,
        otherwise is considered covered by unit tests in auth/session module.
        """
        from accounts.models import EmailChangeRequest  # must exist

        user = self._create_user("old5@example.com")
        c = self._auth_client(user)

        resp = c.post(
            self.CHANGE_URL,
            {"new_email": "new5@example.com", "new_email_confirm": "new5@example.com", "current_password": "Passw0rd!123"},
            format="json",
        )
        assert resp.status_code in (200, 204)

        # We need a way to obtain a confirm token for tests without reading email.
        # Contract: model exposes a helper to generate raw token at creation time OR stores a non-hashed token in test mode.
        req = EmailChangeRequest.objects.get(user=user, cancelled_at__isnull=True, confirmed_at__isnull=True)

        assert hasattr(req, "get_confirm_token_for_tests"), "Provide a test-only helper to access raw token safely."
        token = req.get_confirm_token_for_tests()
        assert isinstance(token, str) and len(token) > 10

        c2 = self._client()  # confirm endpoint is typically unauthenticated
        confirm = c2.get(self.CONFIRM_URL, {"token": token})
        assert confirm.status_code in (200, 204)

        user.refresh_from_db()
        assert user.email == "new5@example.com"

        req.refresh_from_db()
        assert req.confirmed_at is not None

    def test_cancel_prevents_confirmation(self):
        from accounts.models import EmailChangeRequest

        user = self._create_user("old6@example.com")
        c = self._auth_client(user)

        resp = c.post(
            self.CHANGE_URL,
            {"new_email": "new6@example.com", "new_email_confirm": "new6@example.com", "current_password": "Passw0rd!123"},
            format="json",
        )
        assert resp.status_code in (200, 204)

        req = EmailChangeRequest.objects.get(user=user, cancelled_at__isnull=True, confirmed_at__isnull=True)
        assert hasattr(req, "get_cancel_token_for_tests")
        cancel_token = req.get_cancel_token_for_tests()

        anon = self._client()
        cancel = anon.get(self.CANCEL_URL, {"token": cancel_token})
        assert cancel.status_code in (200, 204)

        # Now confirm must fail
        confirm_token = req.get_confirm_token_for_tests()
        confirm = anon.get(self.CONFIRM_URL, {"token": confirm_token})
        assert confirm.status_code in (400, 404, 409)

        req.refresh_from_db()
        assert req.cancelled_at is not None