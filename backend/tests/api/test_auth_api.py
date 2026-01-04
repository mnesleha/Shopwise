import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_register_creates_user_and_returns_basic_user_info():
    client = APIClient()

    payload = {"username": "newuser", "password": "Passw0rd!123"}
    r = client.post("/api/v1/auth/register/", payload, format="json")

    assert r.status_code == 201
    data = r.json()

    # Response: basic user info, no secrets
    assert "id" in data
    assert data["username"] == "newuser"
    assert "password" not in data
    # email is optional -> may be missing or null; do not enforce.

    # User created in DB
    assert User.objects.filter(username="newuser").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload, expected_error_fields",
    [
        ({"password": "Passw0rd!123"}, ["username"]),
        ({"username": "newuser"}, ["password"]),
        ({}, ["username", "password"]),
    ],
)
def test_register_validation_errors(payload, expected_error_fields):
    client = APIClient()

    r = client.post("/api/v1/auth/register/", payload, format="json")

    assert r.status_code == 400
    data = r.json()

    # Unified validation error shape
    assert data["code"] == "VALIDATION_ERROR"
    assert "message" in data
    assert "errors" in data
    assert isinstance(data["errors"], dict)

    for field in expected_error_fields:
        assert field in data["errors"]


@pytest.mark.django_db
def test_register_duplicate_username_returns_validation_error_in_unified_shape():
    client = APIClient()

    # first registration
    r1 = client.post(
        "/api/v1/auth/register/",
        {"username": "dupuser", "password": "Passw0rd!123"},
        format="json",
    )
    assert r1.status_code == 201

    # second registration with same username
    r2 = client.post(
        "/api/v1/auth/register/",
        {"username": "dupuser", "password": "DifferentPass!456"},
        format="json",
    )

    assert r2.status_code == 400
    data = r2.json()

    assert data["code"] == "VALIDATION_ERROR"
    assert "errors" in data
    assert isinstance(data["errors"], dict)
    assert "username" in data["errors"]


@pytest.mark.django_db
def test_login_returns_bearer_token_for_valid_credentials():
    # Precondition: user exists
    User.objects.create_user(username="loginuser", password="Passw0rd!123")

    client = APIClient()
    r = client.post(
        "/api/v1/auth/login/",
        {"username": "loginuser", "password": "Passw0rd!123"},
        format="json",
    )

    assert r.status_code == 200
    data = r.json()

    # JWT token response (minimal contract)
    assert "access" in data
    assert isinstance(data["access"], str)
    assert len(data["access"]) > 10  # looks like a token


@pytest.mark.django_db
def test_login_invalid_credentials_returns_validation_error_shape():
    User.objects.create_user(username="loginuser", password="CorrectPass!123")

    client = APIClient()
    r = client.post(
        "/api/v1/auth/login/",
        {"username": "loginuser", "password": "WrongPass!123"},
        format="json",
    )

    assert r.status_code == 400
    data = r.json()

    assert data["code"] == "VALIDATION_ERROR"
    assert "message" in data
    assert "errors" in data
    assert isinstance(data["errors"], dict)
    # business-level check: must communicate invalid credentials in a structured way
    assert "non_field_errors" in data["errors"]


@pytest.mark.django_db
def test_me_returns_current_user_identity_when_authenticated_via_bearer_token():
    User.objects.create_user(username="meuser", password="Passw0rd!123")

    client = APIClient()

    # login -> get token
    login_r = client.post(
        "/api/v1/auth/login/",
        {"username": "meuser", "password": "Passw0rd!123"},
        format="json",
    )
    assert login_r.status_code == 200
    access = login_r.json()["access"]

    # call /me with Bearer token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me_r = client.get("/api/v1/auth/me/")

    assert me_r.status_code == 200
    data = me_r.json()

    assert "id" in data
    assert data["username"] == "meuser"
    # email optional; do not enforce.
    # role may be added later; do not enforce here.


@pytest.mark.django_db
def test_me_requires_authentication():
    client = APIClient()
    r = client.get("/api/v1/auth/me/")

    # JWT auth should reject unauthenticated calls
    assert r.status_code in (401, 403)

    data = r.json()
    assert "code" in data and "message" in data
    # DRF commonly uses 'not_authenticated' -> our handler uppercases it
    assert data["code"] in ("NOT_AUTHENTICATED",
                            "AUTHENTICATION_FAILED", "PERMISSION_DENIED")
