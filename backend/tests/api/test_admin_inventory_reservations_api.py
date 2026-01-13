import pytest
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.utils import timezone

from orders.models import InventoryReservation, Order
from products.models import Product
from tests.conftest import create_valid_order


def _login_as(client: APIClient, *, email: str, password: str) -> None:
    r = client.post("/api/v1/auth/login/",
                    {"email": email, "password": password}, format="json")
    assert r.status_code == 200, r.content
    token = r.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


@pytest.mark.django_db
def test_admin_can_list_inventory_reservations():
    User = get_user_model()
    admin = User.objects.create_user(
        email="admin@example.com", password="Passw0rd!123", is_staff=True)

    client = APIClient()
    _login_as(client, email=admin.email, password="Passw0rd!123")

    product = Product.objects.create(
        name="P", price=100, stock_quantity=10, is_active=True)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=timezone.now(),
        status=InventoryReservation.Status.ACTIVE,
    )

    resp = client.get("/api/v1/admin/inventory-reservations/")
    assert resp.status_code == 200
    data = resp.json()
    items = data["results"] if isinstance(
        data, dict) and "results" in data else data
    assert len(items) >= 1


@pytest.mark.django_db
def test_non_admin_cannot_list_inventory_reservations(user):
    client = APIClient()
    _login_as(client, email=user.email, password="Passw0rd!123")

    resp = client.get("/api/v1/admin/inventory-reservations/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_admin_can_retrieve_inventory_reservation_detail():
    User = get_user_model()
    admin = User.objects.create_user(
        email="admin@example.com", password="Passw0rd!123", is_staff=True)

    client = APIClient()
    _login_as(client, email=admin.email, password="Passw0rd!123")

    product = Product.objects.create(
        name="P", price=100, stock_quantity=10, is_active=True)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")
    r = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=2,
        expires_at=timezone.now(),
        status=InventoryReservation.Status.ACTIVE,
    )

    resp = client.get(f"/api/v1/admin/inventory-reservations/{r.id}/")
    assert resp.status_code == 200
    body = resp.json()

    assert body["id"] == r.id
    # depending on serializer naming
    assert body.get("order") in (order.id, str(order.id)
                                 ) or body.get("order_id") == order.id
    assert body.get("product") in (product.id, str(product.id)
                                   ) or body.get("product_id") == product.id
    assert body["status"] == InventoryReservation.Status.ACTIVE
    assert body["quantity"] == 2
