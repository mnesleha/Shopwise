"""
Tests for POST /api/v1/descriptions/upload/ (Martor markdown image upload).

Covers:
- Staff/admin user upload succeeds and response contains "link".
- Unauthenticated requests are denied (401/403).
- Authenticated non-staff requests are denied (401/403).
- Uploading an unsupported file type returns 400.
- Saved file path starts with the configured MARTOR_UPLOAD_PATH.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

User = get_user_model()

_UPLOAD_URL = "/api/v1/descriptions/upload/"

# Minimal 1×1 white PNG (67 bytes) — valid content, no library required.
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x18\xddgE\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_png(name: str = "photo.png") -> SimpleUploadedFile:
    """Return a minimal PNG file suitable for upload tests."""
    return SimpleUploadedFile(name, _TINY_PNG, content_type="image/png")


def _login_as(client: APIClient, *, email: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
    )
    assert response.status_code == 200, response.content
    token = response.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


@pytest.mark.django_db
def test_staff_upload_succeeds_and_returns_link(tmp_path):
    """Staff user POST returns 200 with a 'link' key."""
    staff = User.objects.create_user(
        email="staff@example.com", password="Passw0rd!123", is_staff=True
    )
    client = APIClient()
    _login_as(client, email=staff.email, password="Passw0rd!123")

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        response = client.post(
            _UPLOAD_URL,
            {"markdown-image-upload": _make_png()},
            format="multipart",
        )

    assert response.status_code == 200
    data = response.json()
    assert "link" in data
    assert data["link"]  # non-empty URL


@pytest.mark.django_db
def test_anonymous_upload_is_denied():
    """Unauthenticated request must be rejected."""
    client = APIClient()
    response = client.post(
        _UPLOAD_URL,
        {"markdown-image-upload": _make_png()},
        format="multipart",
    )
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_non_staff_upload_is_denied():
    """Authenticated user without is_staff must be rejected."""
    regular = User.objects.create_user(
        email="regular@example.com", password="Passw0rd!123", is_staff=False
    )
    client = APIClient()
    _login_as(client, email=regular.email, password="Passw0rd!123")

    response = client.post(
        _UPLOAD_URL,
        {"markdown-image-upload": _make_png()},
        format="multipart",
    )
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_invalid_file_type_returns_400(tmp_path):
    """Uploading a non-image file type must return 400."""
    staff = User.objects.create_user(
        email="staff2@example.com", password="Passw0rd!123", is_staff=True
    )
    client = APIClient()
    _login_as(client, email=staff.email, password="Passw0rd!123")

    bad_file = SimpleUploadedFile(
        "malware.exe", b"MZ\x90\x00", content_type="application/octet-stream"
    )

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        response = client.post(
            _UPLOAD_URL,
            {"markdown-image-upload": bad_file},
            format="multipart",
        )

    assert response.status_code == 400


@pytest.mark.django_db
def test_uploaded_file_path_starts_with_upload_path(tmp_path):
    """
    The link returned by the endpoint must reference a path that starts with
    the configured MARTOR_UPLOAD_PATH (products/descriptions).
    """
    staff = User.objects.create_user(
        email="staff3@example.com", password="Passw0rd!123", is_staff=True
    )
    client = APIClient()
    _login_as(client, email=staff.email, password="Passw0rd!123")

    with override_settings(
        MEDIA_ROOT=str(tmp_path),
        MARTOR_UPLOAD_PATH="products/descriptions",
    ):
        response = client.post(
            _UPLOAD_URL,
            {"markdown-image-upload": _make_png()},
            format="multipart",
        )

    assert response.status_code == 200
    link = response.json()["link"]
    # The URL should contain the upload path segment.
    assert "products/descriptions" in link
