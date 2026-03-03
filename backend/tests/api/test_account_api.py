import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.sqlite
class TestAccountAPI:
    ACCOUNT_URL = "/api/v1/account/"

    def _client(self) -> APIClient:
        return APIClient()

    def _create_user(self, email: str = "user@example.com", password: str = "Passw0rd!123", **kwargs):
        User = get_user_model()
        return User.objects.create_user(email=email, password=password, **kwargs)

    def _auth_client(self, user):
        client = self._client()
        client.force_authenticate(user=user)
        return client

    def test_anonymous_cannot_access_account(self):
        client = self._client()
        resp = client.get(self.ACCOUNT_URL)
        assert resp.status_code == 401

        resp = client.patch(self.ACCOUNT_URL, {"first_name": "A"}, format="json")
        assert resp.status_code == 401

    def test_authenticated_can_get_account(self):
        user = self._create_user("acc_1@example.com", first_name="John", last_name="Smith")
        client = self._auth_client(user)

        resp = client.get(self.ACCOUNT_URL)
        assert resp.status_code == 200, resp.data

        # Contract: email and names are returned.
        assert resp.data["email"] == "acc_1@example.com"
        assert resp.data["first_name"] == "John"
        assert resp.data["last_name"] == "Smith"

        # Optional but useful: email_verified is included (read-only).
        assert "email_verified" in resp.data

    def test_authenticated_can_patch_first_and_last_name(self):
        user = self._create_user("acc_2@example.com", first_name="Old", last_name="Name")
        client = self._auth_client(user)

        resp = client.patch(
            self.ACCOUNT_URL,
            {"first_name": "New", "last_name": "User"},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["first_name"] == "New"
        assert resp.data["last_name"] == "User"
        assert resp.data["email"] == "acc_2@example.com"

        user.refresh_from_db()
        assert user.first_name == "New"
        assert user.last_name == "User"

    def test_patch_rejects_email_change(self):
        user = self._create_user("acc_3@example.com", first_name="A", last_name="B")
        client = self._auth_client(user)

        resp = client.patch(
            self.ACCOUNT_URL,
            {"email": "hacker@example.com"},
            format="json",
        )
        assert resp.status_code == 400, resp.data

        user.refresh_from_db()
        assert user.email == "acc_3@example.com"