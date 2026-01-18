import pytest
from django.db import IntegrityError
from orders.models import Order
from payments.models import Payment
from orders.services.order_service import OrderService
from api.exceptions.payment import PaymentAlreadyExistsException


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
def test_payment_allows_multiple_attempts_but_blocks_second_success(order_factory, user):
    """
    Payment attempts semantics:
    - multiple FAILED attempts per order are allowed (retry)
    - once a SUCCESS payment exists, further payment attempts are blocked by service logic
    """
    order = order_factory(user=user, status=Order.Status.CREATED)

    # multiple failed attempts are allowed at DB level
    Payment.objects.create(order=order, status=Payment.Status.FAILED)
    Payment.objects.create(order=order, status=Payment.Status.FAILED)
    assert Payment.objects.filter(order=order).count() == 2

    # first success attempt via service should work
    OrderService.create_payment_and_apply_result(
        order=order, result="success", actor_user=user)
    assert Payment.objects.filter(
        order=order, status=Payment.Status.SUCCESS).count() == 1

    # second success attempt must be blocked
    with pytest.raises(PaymentAlreadyExistsException):
        OrderService.create_payment_and_apply_result(
            order=order, result="success", actor_user=user)
