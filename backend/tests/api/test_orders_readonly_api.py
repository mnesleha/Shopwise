import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_order_cannot_be_created_directly(auth_client):
    response = auth_client.post("/api/v1/orders/")
    assert response.status_code == 405


@pytest.mark.django_db
def test_order_detail_requires_authentication():
    response = APIClient().get("/api/v1/orders/1/")
    assert response.status_code == 403
