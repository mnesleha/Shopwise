import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tests.conftest import checkout_payload
from accounts.services.email_verification import issue_email_verification_token
from orders.models import Order


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_verify_email_claims_guest_orders_mysql():
    User = get_user_model()
    user = User.objects.create_user(
        email="customer@example.com", password="Passw0rd!123")

    Order.objects.create(
        user=None, **checkout_payload(customer_email="customer@example.com"))

    token = issue_email_verification_token(user)

    client = APIClient()
    res = client.post("/api/v1/auth/verify-email/",
                      {"token": token}, format="json")
    assert res.status_code == 200, res.content
