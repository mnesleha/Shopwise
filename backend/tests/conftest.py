import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient


@pytest.fixture
def user():
    return User.objects.create_user(
        username="testuser",
        password="pass1234",
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client
