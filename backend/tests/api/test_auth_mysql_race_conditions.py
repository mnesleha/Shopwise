import threading
from typing import Any, Dict, Optional, Tuple
import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient


def _post_register(payload: Dict[str, Any], out: Dict[int, Any], idx: int, barrier: threading.Barrier):
    """
    Thread worker that performs POST /auth/register/ and records either:
      (status_code, json) OR ("EXC", repr(exception))
    """
    try:
        # Ensure the thread uses its own DB connection context
        close_old_connections()

        client = APIClient()

        # start both threads at the same time
        barrier.wait()

        r = client.post("/api/v1/auth/register/", payload, format="json")
        data = r.json() if r.content else None
        out[idx] = (r.status_code, data)

    except Exception as e:
        out[idx] = ("EXC", repr(e))


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_register_username_race_condition_never_returns_500_and_is_controlled():
    payload = {"username": "raceuser", "password": "Passw0rd!123"}

    results: Dict[int, Any] = {}
    barrier = threading.Barrier(2)

    t1 = threading.Thread(target=_post_register,
                          args=(payload, results, 0, barrier))
    t2 = threading.Thread(target=_post_register,
                          args=(payload, results, 1, barrier))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert 0 in results and 1 in results, f"Thread results missing: {results}"

    # If any thread raised, fail with details (so it's debuggable)
    if results[0][0] == "EXC" or results[1][0] == "EXC":
        pytest.fail(f"Thread exception(s): {results}")

    statuses = sorted([results[0][0], results[1][0]])

    # username has DB unique constraint -> exactly one should succeed
    assert statuses == [201, 400], f"Unexpected statuses/results: {results}"

    # ensure failing response is controlled (no 500, correct shape)
    failing = results[0] if results[0][0] == 400 else results[1]
    data = failing[1]

    assert data["code"] == "VALIDATION_ERROR"
    assert "message" in data
    assert "errors" in data
    assert "username" in data["errors"]


@pytest.mark.mysql
@pytest.mark.django_db
def test_register_duplicate_email_sequential_returns_validation_error():
    client = APIClient()

    r1 = client.post(
        "/api/v1/auth/register/",
        {"username": "emailuser1", "password": "Passw0rd!123",
            "email": "dup@example.com"},
        format="json",
    )
    assert r1.status_code == 201

    r2 = client.post(
        "/api/v1/auth/register/",
        {"username": "emailuser2", "password": "Passw0rd!123",
            "email": "dup@example.com"},
        format="json",
    )
    assert r2.status_code == 400
    data = r2.json()

    assert data["code"] == "VALIDATION_ERROR"
    assert "errors" in data
    assert "email" in data["errors"]


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
@pytest.mark.xfail(reason="Email is only app-level unique (validator). Without DB unique constraint, race can allow duplicates.")
def test_register_email_race_condition_expected_to_fail_without_db_unique_constraint():
    payload1 = {"username": "raceemail1",
                "password": "Passw0rd!123", "email": "race@example.com"}
    payload2 = {"username": "raceemail2",
                "password": "Passw0rd!123", "email": "race@example.com"}

    results = {}
    barrier = threading.Barrier(2)

    def worker(payload, idx):
        close_old_connections()
        client = APIClient()
        barrier.wait()
        r = client.post("/api/v1/auth/register/", payload, format="json")
        results[idx] = r.status_code

    t1 = threading.Thread(target=worker, args=(payload1, 0))
    t2 = threading.Thread(target=worker, args=(payload2, 1))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert sorted([results[0], results[1]]) == [201, 400]
