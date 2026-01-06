import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
ME_URL = "/api/v1/auth/me/"
REFRESH_URL = "/api/v1/auth/refresh/"


@pytest.mark.django_db
def test_register_creates_user_and_returns_basic_identity():
    client = APIClient()

    payload = {
        "email": "Customer1@Example.com",
        "password": "Passw0rd!123",
        "first_name": "John",
        "last_name": "Doe",
    }
    response = client.post(REGISTER_URL, payload, format="json")
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["email"] == "customer1@example.com"
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["role"] == "CUSTOMER"

    User = get_user_model()
    user = User.objects.get(email="customer1@example.com")
    assert user.check_password("Passw0rd!123") is True


@pytest.mark.django_db
def test_register_requires_email_and_password():
    client = APIClient()

    response = client.post(REGISTER_URL, {}, format="json")
    assert response.status_code == 400

    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "errors" in body
    assert "email" in body["errors"]
    assert "password" in body["errors"]


@pytest.mark.django_db
def test_register_rejects_duplicate_email_with_400_and_error_shape():
    client = APIClient()
    payload = {
        "email": "dup@example.com",
        "password": "Passw0rd!123",
        "first_name": "A",
        "last_name": "B",
    }

    first = client.post(REGISTER_URL, payload, format="json")
    assert first.status_code == 201

    second = client.post(REGISTER_URL, payload, format="json")
    assert second.status_code == 400

    body = second.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "errors" in body
    assert "email" in body["errors"]


@pytest.mark.django_db
def test_login_by_email_returns_access_and_refresh_tokens():
    client = APIClient()

    # Register first
    client.post(
        REGISTER_URL,
        {
            "email": "login@example.com",
            "password": "Passw0rd!123",
            "first_name": "First",
            "last_name": "Last",
        },
        format="json",
    )

    # Login
    response = client.post(
        LOGIN_URL,
        {"email": "LOGIN@EXAMPLE.COM", "password": "Passw0rd!123"},
        format="json",
    )
    assert response.status_code == 200

    body = response.json()
    assert "access" in body
    assert "refresh" in body
    assert isinstance(body["access"], str) and body["access"]
    assert isinstance(body["refresh"], str) and body["refresh"]


@pytest.mark.django_db
def test_login_invalid_credentials_returns_400_with_error_shape():
    client = APIClient()

    # no user exists
    response = client.post(
        LOGIN_URL,
        {"email": "missing@example.com", "password": "wrong"},
        format="json",
    )
    assert response.status_code == 400

    body = response.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    assert "message" in body


@pytest.mark.django_db
def test_me_requires_authentication_401_with_error_shape():
    client = APIClient()

    response = client.get(ME_URL)
    assert response.status_code == 401

    body = response.json()
    assert body["code"] == "NOT_AUTHENTICATED"
    assert "message" in body


@pytest.mark.django_db
def test_me_returns_current_user_identity_when_authenticated():
    client = APIClient()

    client.post(
        REGISTER_URL,
        {
            "email": "me@example.com",
            "password": "Passw0rd!123",
            "first_name": "Me",
            "last_name": "User",
        },
        format="json",
    )

    login = client.post(
        LOGIN_URL,
        {"email": "me@example.com", "password": "Passw0rd!123"},
        format="json",
    )
    assert login.status_code == 200
    tokens = login.json()

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = client.get(ME_URL)
    assert response.status_code == 200

    body = response.json()
    assert "id" in body
    assert body["email"] == "me@example.com"
    assert body["first_name"] == "Me"
    assert body["last_name"] == "User"
    assert body["role"] == "CUSTOMER"


@pytest.mark.django_db
def test_refresh_rotates_refresh_and_old_refresh_is_rejected():
    """
    Contract:
    - /refresh returns a new access token and (when rotation enabled) a new refresh token.
    - old refresh token must become unusable (blacklisted) when BLACKLIST_AFTER_ROTATION=True.
    """
    client = APIClient()

    client.post(
        REGISTER_URL,
        {
            "email": "refresh@example.com",
            "password": "Passw0rd!123",
            "first_name": "R",
            "last_name": "T",
        },
        format="json",
    )

    login = client.post(
        LOGIN_URL,
        {"email": "refresh@example.com", "password": "Passw0rd!123"},
        format="json",
    )
    assert login.status_code == 200
    first_tokens = login.json()

    old_refresh = first_tokens["refresh"]

    # First refresh (should rotate)
    r1 = client.post(REFRESH_URL, {"refresh": old_refresh}, format="json")
    assert r1.status_code == 200
    tokens_2 = r1.json()
    assert "access" in tokens_2
    assert "refresh" in tokens_2
    assert tokens_2["refresh"] != old_refresh

    # Second refresh using OLD refresh should fail
    r2 = client.post(REFRESH_URL, {"refresh": old_refresh}, format="json")
    assert r2.status_code in (400, 401)

    body = r2.json()
    # validation errors should follow unified shape
    assert body["code"] in (
        "VALIDATION_ERROR", "TOKEN_INVALID", "INVALID_TOKEN", "NOT_AUTHENTICATED")
    assert "message" in body
