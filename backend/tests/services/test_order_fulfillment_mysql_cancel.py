import pytest
from django.db import transaction

from orders.models import Order
from orders.services.order_service import OrderService


pytestmark = pytest.mark.mysql


@pytest.mark.django_db(transaction=True)
def test_admin_cancel_is_atomic_mysql(order_factory, user):
    order = order_factory(user=user, status=Order.Status.CREATED)

    with transaction.atomic():
        OrderService.cancel_by_admin(order=order, actor_user=user)

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert order.cancelled_by == Order.CancelledBy.ADMIN
