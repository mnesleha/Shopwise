import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.sqlite
class TestCartMergeReportV1:
    MERGE_URL = "/api/v1/cart/merge/"

    def _client(self) -> APIClient:
        return APIClient()

    def _create_user(self, email="u@example.com", password="Passw0rd!123"):
        User = get_user_model()
        return User.objects.create_user(email=email, password=password)

    def _auth_client(self, user):
        c = self._client()
        c.force_authenticate(user=user)
        return c

    def test_anonymous_cannot_merge(self):
        c = self._client()
        r = c.post(self.MERGE_URL, {}, format="json")
        assert r.status_code == 401

    def test_merge_without_guest_token_returns_noop_report(self):
        """
        Contract:
        If no guest token exists, endpoint returns 200 with performed=false, result=NOOP.
        No mock needed — sending no token header/cookie is sufficient.
        """
        user = self._create_user("merge_1@example.com")
        c = self._auth_client(user)

        r = c.post(self.MERGE_URL, {}, format="json")
        assert r.status_code == 200, r.data
        assert r.data["performed"] is False
        assert r.data["result"] == "NOOP"
        assert r.data["items_added"] == 0
        assert r.data["items_updated"] == 0
        assert r.data["items_removed"] == 0
        assert r.data["warnings"] == []

    def test_stock_adjustment_is_reported_as_warning_not_error(self, monkeypatch):
        """
        Contract:
        Insufficient stock does NOT cause 409.
        Quantities are capped and report contains STOCK_ADJUSTED warning.
        """
        user = self._create_user("merge_2@example.com")
        c = self._auth_client(user)

        # Mock merge service to return a report with warning.
        report = {
            "performed": True,
            "result": "MERGED",
            "items_added": 0,
            "items_updated": 1,
            "items_removed": 0,
            "warnings": [{"code": "STOCK_ADJUSTED", "product_id": 125, "requested": 3, "applied": 1}],
        }

        import api.views.auth as auth_views
        monkeypatch.setattr(auth_views, "extract_cart_token", lambda request: "token123")
        monkeypatch.setattr(auth_views, "merge_or_adopt_guest_cart", lambda user, raw_token: report)

        r = c.post(self.MERGE_URL, {}, format="json")
        assert r.status_code == 200, r.data
        assert r.data["performed"] is True
        assert r.data["warnings"][0]["code"] == "STOCK_ADJUSTED"
