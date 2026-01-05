import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_order_cannot_be_created_directly(auth_client):
    response = auth_client.post("/api/v1/orders/")
    assert response.status_code == 405


@pytest.mark.django_db
def test_order_detail_requires_authentication():
    response = APIClient().get("/api/v1/orders/1/")
    data = response.json()

    assert "code" in data
    assert "message" in data
    assert isinstance(data["code"], str)
    assert isinstance(data["message"], str)
    # Accept common DRF/JWT auth codes mapped by the global handler
    assert data["code"] in ("NOT_AUTHENTICATED", "AUTHENTICATION_FAILED")

    assert response.status_code == 401
