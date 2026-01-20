import threading
from dataclasses import dataclass
from typing import List

import pytest
from django.db import connections, transaction
from django.utils import timezone
from django_q.tasks import async_task

try:
    from django_q.models import OrmQ
except Exception:  # pragma: no cover
    OrmQ = None  # type: ignore


pytestmark = pytest.mark.mysql


def _dummy_task(x: int) -> int:
    return x + 1


@dataclass
class _Attempt:
    ok: bool
    rowcount: int
    error: str | None = None


def _cas_lock_update(table: str, queue_id: int, initial_lock, results: List[_Attempt], idx: int) -> None:
    """
    Compare-and-swap update:
    - only succeeds if lock value is still exactly the initial value we observed
    - exactly one concurrent contender should succeed (rowcount == 1)
    """
    try:
        conn = connections["default"]
        with transaction.atomic(using="default"):
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE {table}
                    SET `lock` = %s
                    WHERE id = %s AND `lock` = %s
                    """,
                    [timezone.now(), queue_id, initial_lock],
                )
                rc = cur.rowcount
        results[idx] = _Attempt(ok=True, rowcount=rc)
    except Exception as e:  # pragma: no cover
        results[idx] = _Attempt(ok=False, rowcount=0, error=str(e))


@pytest.mark.skipif(OrmQ is None, reason="django-q2 OrmQ model not available")
@pytest.mark.django_db(transaction=True)
def test_q2_orm_broker_enqueue_creates_queue_row_mysql(settings):
    settings.Q_CLUSTER = {
        **getattr(settings, "Q_CLUSTER", {}), "orm": "default", "sync": False}

    before = OrmQ.objects.using("default").count()
    async_task(_dummy_task, 123)
    after = OrmQ.objects.using("default").count()

    assert after == before + 1
    newest = OrmQ.objects.using("default").order_by("-id").first()
    assert newest is not None
    # Do not assert anything about newest.lock (implementation detail)


@pytest.mark.skipif(OrmQ is None, reason="django-q2 OrmQ model not available")
@pytest.mark.django_db(transaction=True)
def test_q2_orm_broker_lock_update_is_exclusive_via_cas_mysql(settings):
    """
    MySQL-specific concurrency guarantee for DB-as-broker:
    Only one contender should be able to 'claim' the same row using an atomic CAS update.

    This test is robust to django-q2 variations where OrmQ.lock is already set at enqueue time.
    """
    settings.Q_CLUSTER = {
        **getattr(settings, "Q_CLUSTER", {}), "orm": "default", "sync": False}

    async_task(_dummy_task, 1)
    row = OrmQ.objects.using("default").order_by("-id").first()
    assert row is not None
    assert row.lock is not None  # in your environment this is true

    table = OrmQ._meta.db_table
    initial_lock = row.lock

    results: List[_Attempt] = [
        _Attempt(ok=False, rowcount=0), _Attempt(ok=False, rowcount=0)]
    t1 = threading.Thread(target=_cas_lock_update, args=(
        table, row.id, initial_lock, results, 0))
    t2 = threading.Thread(target=_cas_lock_update, args=(
        table, row.id, initial_lock, results, 1))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results[0].ok and results[1].ok, f"CAS contenders failed: {results}"
    rowcounts = sorted([results[0].rowcount, results[1].rowcount])
    assert rowcounts == [
        0, 1], f"Expected exactly one winner (1) and one loser (0), got: {rowcounts}"

    row.refresh_from_db()
    assert row.lock != initial_lock  # winner updated lock timestamp


@pytest.mark.skipif(OrmQ is None, reason="django-q2 OrmQ model not available")
@pytest.mark.django_db(transaction=True)
def test_q2_orm_broker_cas_is_idempotent_after_first_claim_mysql(settings):
    """
    After the first successful CAS update, repeating CAS with the original initial_lock must not succeed.
    """
    settings.Q_CLUSTER = {
        **getattr(settings, "Q_CLUSTER", {}), "orm": "default", "sync": False}

    async_task(_dummy_task, 99)
    row = OrmQ.objects.using("default").order_by("-id").first()
    assert row is not None
    assert row.lock is not None

    table = OrmQ._meta.db_table
    initial_lock = row.lock

    # First CAS should succeed
    r1: List[_Attempt] = [_Attempt(ok=False, rowcount=0)]
    _cas_lock_update(table, row.id, initial_lock, r1, 0)
    assert r1[0].ok and r1[0].rowcount == 1

    # Second CAS with same initial_lock must fail (already changed)
    r2: List[_Attempt] = [_Attempt(ok=False, rowcount=0)]
    _cas_lock_update(table, row.id, initial_lock, r2, 0)
    assert r2[0].ok and r2[0].rowcount == 0
