import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_healthcheck_endpoint(client):
    response = client.get("/health/")
    assert response.status_code == 200
