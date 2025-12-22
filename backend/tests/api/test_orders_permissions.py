import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_orders_requires_authentication():
    client = APIClient()
    response = client.post("/api/v1/orders/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_authenticated_user_can_create_order():
    user = User.objects.create_user(
        username="testuser",
        password="pass1234",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/v1/orders/")
    assert response.status_code == 201


def test_unauthenticated_user_cannot_create_order():
    client = APIClient()
    response = client.post("/api/v1/orders/")
    assert response.status_code == 403
