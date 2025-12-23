import pytest


@pytest.mark.django_db
def test_order_cannot_be_created_directly(auth_client):
    response = auth_client.post("/api/v1/orders/")
    assert response.status_code == 405
