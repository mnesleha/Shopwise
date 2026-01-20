import pytest
from django.db import transaction
from django_q.tasks import async_task

try:
    from django_q.models import OrmQ
except Exception:  # pragma: no cover
    OrmQ = None  # type: ignore


pytestmark = pytest.mark.mysql


@pytest.mark.skipif(OrmQ is None, reason="django-q2 OrmQ model not available")
@pytest.mark.django_db(transaction=True)
def test_notifications_enqueue_happens_only_after_commit_mysql(settings):
    """
    In production we use django-q2 ORM broker on the default DB.
    The critical guarantee: enqueue happens only after the surrounding DB transaction commits.
    """
    settings.Q_CLUSTER = {
        **getattr(settings, "Q_CLUSTER", {}),
        "orm": "default",
        "sync": False,  # do not execute inline
    }

    before = OrmQ.objects.using("default").count()

    with transaction.atomic():
        transaction.on_commit(
            lambda: async_task(
                "notifications.jobs.send_email_verification",
                recipient_email="alice@example.com",
                verification_url="https://example.test/verify-email?token=abc123",
            )
        )
        # Still inside transaction: nothing must be enqueued yet
        assert OrmQ.objects.using("default").count() == before

    # After commit: exactly one queue row must exist
    after = OrmQ.objects.using("default").count()
    assert after == before + 1

    newest = OrmQ.objects.using("default").order_by("-id").first()
    assert newest is not None


@pytest.mark.skipif(OrmQ is None, reason="django-q2 OrmQ model not available")
@pytest.mark.django_db(transaction=True)
def test_notifications_enqueue_does_not_happen_on_rollback_mysql(settings):
    """
    If the transaction rolls back, we must NOT enqueue the notification job.
    This protects us from sending emails for state changes that never committed.
    """
    settings.Q_CLUSTER = {
        **getattr(settings, "Q_CLUSTER", {}),
        "orm": "default",
        "sync": False,
    }

    before = OrmQ.objects.using("default").count()

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            transaction.on_commit(
                lambda: async_task(
                    "notifications.jobs.send_guest_order_link",
                    recipient_email="guest@example.com",
                    order_number="SW-10001",
                    guest_order_url="https://example.test/orders/123?token=tok_456",
                )
            )
            raise RuntimeError("force rollback")

    after = OrmQ.objects.using("default").count()
    assert after == before


@pytest.mark.skipif(OrmQ is None, reason="django-q2 OrmQ model not available")
@pytest.mark.django_db(transaction=True)
def test_notifications_on_commit_executes_after_outer_commit_mysql(settings):
    """
    Nested atomic blocks must not enqueue until the OUTER transaction commits.
    This matters when service methods use internal atomic blocks.
    """
    settings.Q_CLUSTER = {
        **getattr(settings, "Q_CLUSTER", {}),
        "orm": "default",
        "sync": False,
    }

    before = OrmQ.objects.using("default").count()

    with transaction.atomic():
        with transaction.atomic():
            transaction.on_commit(
                lambda: async_task(
                    "notifications.jobs.send_email_verification",
                    recipient_email="nested@example.com",
                    verification_url="https://example.test/verify-email?token=nested",
                )
            )
            # Still inside inner block: nothing enqueued yet
            assert OrmQ.objects.using("default").count() == before

        # After inner commit but before outer commit: still nothing enqueued
        assert OrmQ.objects.using("default").count() == before

    # After outer commit: now it must be enqueued
    after = OrmQ.objects.using("default").count()
    assert after == before + 1
