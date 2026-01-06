import pytest
from payments.models import Payment
from orders.models import Order
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_payment_created_with_default_status():

    User = get_user_model()
    user = User.objects.create_user(
        email="payuser1@example.com", password="pass")
    order = Order.objects.create(user=user)

    payment = Payment.objects.create(order=order)

    assert payment.status == Payment.Status.PENDING


@pytest.mark.django_db
def test_payment_must_have_order():

    payment = Payment(order=None)

    with pytest.raises(ValidationError):
        payment.full_clean()


@pytest.mark.django_db
def test_payment_invalid_status_is_rejected():

    User = get_user_model()
    user = User.objects.create_user(
        email="payuser2@example.com", password="pass")
    order = Order.objects.create(user=user)

    payment = Payment(
        order=order,
        status="INVALID",
    )

    with pytest.raises(ValidationError):
        payment.full_clean()


@pytest.mark.django_db
def test_valid_payment_is_valid():

    User = get_user_model()
    user = User.objects.create_user(
        email="payuser3@example.com", password="pass")
    order = Order.objects.create(user=user)

    payment = Payment(
        order=order,
        status=Payment.Status.PENDING,
    )

    payment.full_clean()  # should not raise
