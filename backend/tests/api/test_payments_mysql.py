import pytest
from django.db import IntegrityError
from orders.models import Order
from payments.models import Payment


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_payment_double_submit_mysql_returns_409(auth_client, user, order_factory):
    order = order_factory(user=user, status=Order.Status.CREATED)

    payload = {"order_id": order.id, "result": "success"}
    r1 = auth_client.post("/api/v1/payments/", payload, format="json")
    r2 = auth_client.post("/api/v1/payments/", payload, format="json")

    assert r1.status_code == 201
    assert r2.status_code == 409


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_payment_is_one_to_one_with_order_mysql(order_factory, user):
    """
    DB-level guard: there must not be two payments for the same order.
    """
    order = order_factory(user=user, status=Order.Status.CREATED)

    Payment.objects.create(order=order, status=Payment.Status.SUCCESS)

    # Creating another payment for the same order must fail on DB constraint
    with pytest.raises(IntegrityError):
        Payment.objects.create(order=order, status=Payment.Status.FAILED)
