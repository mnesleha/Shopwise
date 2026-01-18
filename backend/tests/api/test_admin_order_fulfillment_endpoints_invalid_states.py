import pytest

from orders.models import Order


pytestmark = pytest.mark.django_db


def _make_staff(user):
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.mark.parametrize(
    "initial_status, endpoint",
    [
        (Order.Status.CREATED, "ship"),
        (Order.Status.PAYMENT_FAILED, "ship"),
        (Order.Status.CANCELLED, "ship"),
        (Order.Status.DELIVERED, "ship"),
        (Order.Status.PAID, "deliver"),
        (Order.Status.CREATED, "deliver"),
        (Order.Status.PAYMENT_FAILED, "deliver"),
        (Order.Status.CANCELLED, "deliver"),
        (Order.Status.DELIVERED, "deliver"),
    ],
)
def test_admin_ship_deliver_invalid_states_return_409(
    auth_client, user, order_factory, initial_status, endpoint
):
    _make_staff(user)
    order = order_factory(user=user, status=initial_status)

    resp = auth_client.post(
        f"/api/v1/admin/orders/{order.id}/{endpoint}/", format="json")
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_ORDER_STATE"
