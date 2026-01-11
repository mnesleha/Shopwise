import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tests.conftest import checkout_payload
from orders.models import Order


@pytest.mark.django_db
def test_login_claims_guest_orders_for_verified_user():
    # guest order exists
    guest = Order.objects.create(
        user=None, **checkout_payload(customer_email="customer@example.com"))

    User = get_user_model()
    user = User.objects.create_user(
        email="customer@example.com", password="Passw0rd!123")
    user.email_verified = True
    user.save(update_fields=["email_verified"])

    client = APIClient()
    login = client.post("/api/v1/auth/login/",
                        {"email": user.email, "password": "Passw0rd!123"}, format="json")
    assert login.status_code == 200, login.content

    guest.refresh_from_db()
    assert guest.user_id == user.id
    assert guest.is_claimed is True
