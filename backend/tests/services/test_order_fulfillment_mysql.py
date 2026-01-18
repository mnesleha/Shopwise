import pytest
from django.db import transaction

from orders.models import Order
from orders.services.order_service import OrderService
from api.exceptions.orders import InvalidOrderStateException


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_ship_is_atomic_and_persists_state_mysql(order_factory, user):
    order = order_factory(user=user, status=Order.Status.PAID)

    with transaction.atomic():
        OrderService.ship_by_admin(order=order, actor_user=user)

    order.refresh_from_db()
    assert order.status == Order.Status.SHIPPED


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_ship_invalid_state_is_409_mysql(order_factory, user):
    order = order_factory(user=user, status=Order.Status.CREATED)

    with pytest.raises(InvalidOrderStateException):
        with transaction.atomic():
            OrderService.ship_by_admin(order=order, actor_user=user)
