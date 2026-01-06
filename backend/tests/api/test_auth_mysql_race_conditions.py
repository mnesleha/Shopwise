import concurrent.futures
import pytest
from rest_framework.test import APIClient

REGISTER_URL = "/api/v1/auth/register/"


def _register(email: str, password: str, first_name: str, last_name: str):
    client = APIClient()
    r = client.post(
        REGISTER_URL,
        {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        },
        format="json",
    )
    try:
        body = r.json()
    except Exception:
        body = None
    return r.status_code, body


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_register_email_race_condition_never_returns_500_and_is_deterministic():
    """
    On MySQL, unique email is enforced at DB level.
    Two concurrent registrations with the same email must result in:
    - one success (201)
    - one validation error (400)
    - never 500
    """
    email = "race@example.com"
    password = "Passw0rd!123"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        futures = [
            ex.submit(_register, email, password, "A", "One"),
            ex.submit(_register, email, password, "B", "Two"),
        ]
        results = [f.result() for f in futures]

    statuses = sorted([results[0][0], results[1][0]])
    assert statuses == [201, 400]

    # ensure the 400 has a unified validation error shape
    bad = results[0] if results[0][0] == 400 else results[1]
    _, body = bad
    assert body is not None
    assert body["code"] == "VALIDATION_ERROR"
    assert "errors" in body
    assert "email" in body["errors"]


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_register_email_race_condition_case_insensitive_normalization():
    """
    Email normalization should be case-insensitive:
    - 'User@X.com' and 'user@x.com' are the same identity.
    Concurrent requests differing only by case must still produce [201, 400].
    """
    password = "Passw0rd!123"
    email1 = "User@Example.com"
    email2 = "user@example.com"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        futures = [
            ex.submit(_register, email1, password, "A", "One"),
            ex.submit(_register, email2, password, "B", "Two"),
        ]
        results = [f.result() for f in futures]

    statuses = sorted([results[0][0], results[1][0]])
    assert statuses == [201, 400]
