from unittest.mock import patch

import pytest
from django.db import transaction

pytestmark = pytest.mark.django_db


def _capture_on_commit(monkeypatch):
    callbacks = []

    def fake_on_commit(fn, using=None):
        callbacks.append(fn)

    monkeypatch.setattr(transaction, "on_commit", fake_on_commit)
    return callbacks


def test_request_email_verification_enqueues_on_commit(client, monkeypatch, settings, django_user_model):
    settings.PUBLIC_BASE_URL = "https://example.test"

    user = django_user_model.objects.create_user(
        email="u1@example.com",
        password="pw",
        email_verified=False,
    )

    callbacks = _capture_on_commit(monkeypatch)

    with patch("api.views.auth.issue_email_verification_token", return_value="tok_123"):
        with patch("notifications.enqueue.async_task") as async_task_mock:
            resp = client.post(
                "/api/v1/auth/request-email-verification/",
                data={"email": "u1@example.com"},
                content_type="application/json",
            )

            assert resp.status_code == 202
            assert resp.json() == {"queued": True}

            assert len(callbacks) == 1
            callbacks[0]()  # simulate commit

            assert async_task_mock.call_count == 1

            job, = async_task_mock.call_args[0]
            assert job == "notifications.jobs.send_email_verification"
            kwargs = async_task_mock.call_args.kwargs
            assert kwargs["recipient_email"] == "u1@example.com"
            assert "verification_url" in kwargs

    args, kwargs = async_task_mock.call_args
    assert args[0] == "notifications.jobs.send_email_verification"
    assert kwargs["recipient_email"] == "u1@example.com"
    assert kwargs["verification_url"] == "https://example.test/api/v1/auth/verify-email/?token=tok_123"
