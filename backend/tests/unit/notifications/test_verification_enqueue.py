from unittest.mock import Mock, patch

import pytest
from django.db import transaction

pytestmark = pytest.mark.django_db


def _capture_on_commit_callback(monkeypatch):
    callbacks = []

    def fake_on_commit(func, using=None):
        callbacks.append(func)

    monkeypatch.setattr(transaction, "on_commit", fake_on_commit)
    return callbacks


def test_request_verification_enqueues_q2_task_on_commit(monkeypatch, client, settings, django_user_model):
    """
    This test asserts wiring behavior:
    - issuing token triggers transaction.on_commit(...)
    - and inside that callback we call django_q.async_task with the expected job dotted path
    """
    callbacks = _capture_on_commit_callback(monkeypatch)

    user = django_user_model.objects.create_user(
        email="u1@example.com", password="pw")
    settings.PUBLIC_BASE_URL = "https://example.test"

    with patch("api.views.auth.async_task") as async_task_mock:
        # Replace this URL with the actual endpoint implemented in PR2:
        # e.g. POST /api/v1/auth/request-email-verification/
        resp = client.post("/api/v1/auth/request-email-verification/",
                           data={"email": "u1@example.com"}, content_type="application/json")

        assert resp.status_code in (200, 202)
        assert len(
            callbacks) == 1, "Expected exactly one transaction.on_commit callback"

        # Simulate DB commit
        callbacks[0]()

        assert async_task_mock.call_count == 1

    args, kwargs = async_task_mock.call_args
    assert args[0] == "notifications.jobs.send_email_verification"
    assert kwargs["recipient_email"] == "u1@example.com"
    assert "verification_url" in kwargs
    assert "https://example.test" in kwargs["verification_url"]
    assert "token=" in kwargs["verification_url"]
