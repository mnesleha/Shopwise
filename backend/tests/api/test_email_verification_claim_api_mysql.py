import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tests.conftest import create_valid_order
from accounts.services.email_verification import issue_email_verification_token


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_verify_email_claims_guest_orders_mysql():
    User = get_user_model()
    user = User.objects.create_user(
        email="customer@example.com", password="Passw0rd!123")

    create_valid_order(
        user=None,
        customer_email="customer@example.com",
    )

    token = issue_email_verification_token(user)

    client = APIClient()
    res = client.post("/api/v1/auth/verify-email/",
                      {"token": token}, format="json")
    assert res.status_code == 200, res.content
