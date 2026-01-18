import pytest

from orders.models import Order


pytestmark = pytest.mark.django_db


def _make_staff(user):
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.mark.parametrize(
    "initial_status",
    [
        Order.Status.PAID,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
        Order.Status.CANCELLED,
    ],
)
def test_admin_cancel_invalid_states_return_409(auth_client, user, order_factory, initial_status):
    _make_staff(user)
    order = order_factory(user=user, status=initial_status)

    resp = auth_client.post(
        f"/api/v1/admin/orders/{order.id}/cancel/", format="json")
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_ORDER_STATE"
