import pytest
from django.db import connection

from auditlog.models import AuditEvent
from auditlog.actions import AuditAction
from auditlog.actors import ActorType


pytestmark = pytest.mark.django_db


# def _skip_if_not_mysql():
#     if connection.vendor != "mysql":
#         pytest.skip(
#             "MySQL-specific auditlog test (connection.vendor != 'mysql').")


@pytest.mark.mysql
@pytest.mark.django_db
def test_audit_event_jsonfield_roundtrip_and_mysql_json_extract():
    """
    MySQL guard:
    - JSONField roundtrip stores and returns dicts correctly (not stringified JSON).
    - MySQL JSON_EXTRACT can read expected keys (ensures real JSON column behavior).
    """
    # _skip_if_not_mysql()

    large_text = "x" * 8000  # large enough to catch edge cases, small enough for CI
    metadata = {
        "cancel_reason": "PAYMENT_EXPIRED",
        "notes": large_text,
        "nested": {"k": "v", "n": 123},
    }
    context = {
        "request_id": "req_test_123",
        "debug": {"a": 1, "b": True},
    }

    ev = AuditEvent.objects.create(
        entity_type="order",
        entity_id="test-order-1",
        action=AuditAction.ORDER_CANCELLED,
        actor_type=ActorType.SYSTEM,
        metadata=metadata,
        context=context,
        scope_key=None,
    )

    ev_db = AuditEvent.objects.get(pk=ev.pk)
    assert ev_db.metadata == metadata
    assert ev_db.context == context

    # MySQL-specific: prove JSON is queryable via JSON_EXTRACT.
    # We read a nested JSON key from metadata and ensure it matches expected value.
    with connection.cursor() as cur:
        # JSON_EXTRACT returns JSON, JSON_UNQUOTE makes it a plain string.
        cur.execute(
            """
            SELECT JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.nested.k'))
            FROM auditlog_auditevent
            WHERE id = %s
            """,
            [ev.pk],
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] == "v"


@pytest.mark.mysql
@pytest.mark.django_db
def test_audit_event_ordering_is_deterministic_with_created_at_and_id():
    """
    MySQL guard:
    - created_at precision can vary; ordering by created_at alone may be unstable.
    - We enforce deterministic ordering by using (created_at DESC, id DESC).
    """
    # _skip_if_not_mysql()

    ev1 = AuditEvent.objects.create(
        entity_type="order",
        entity_id="test-order-2",
        action=AuditAction.ORDER_CANCELLED,
        actor_type=ActorType.SYSTEM,
        metadata={"seq": 1},
        context={},
        scope_key=None,
    )
    ev2 = AuditEvent.objects.create(
        entity_type="order",
        entity_id="test-order-2",
        action=AuditAction.ORDER_CANCELLED,
        actor_type=ActorType.SYSTEM,
        metadata={"seq": 2},
        context={},
        scope_key=None,
    )

    # Deterministic ordering: (created_at, id)
    events = list(
        AuditEvent.objects.filter(
            entity_id="test-order-2").order_by("-created_at", "-id")
    )

    assert len(events) >= 2
    assert events[0].id == ev2.id
    assert events[1].id == ev1.id
