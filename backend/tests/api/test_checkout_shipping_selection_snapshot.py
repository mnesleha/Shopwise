import pytest

from orders.models import Order
from products.models import Product
from shipping.statuses import ShipmentStatus
from tests.conftest import checkout_payload


CHECKOUT_URL = "/api/v1/cart/checkout/"


def _add_product_to_cart(client):
    product = Product.objects.create(
        name="Shipping Selection Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    return product


@pytest.mark.django_db
def test_checkout_success_with_valid_shipping_selection(client):
    _add_product_to_cart(client)

    response = client.post(
        CHECKOUT_URL,
        checkout_payload(
            shipping_provider_code="MOCK",
            shipping_service_code="express",
        ),
        format="json",
    )

    assert response.status_code == 201
    assert response.data["shipping_method"] == {
        "provider_code": "MOCK",
        "service_code": "express",
        "name": "Express",
    }


@pytest.mark.django_db
def test_checkout_rejects_invalid_shipping_provider_code(client):
    _add_product_to_cart(client)

    response = client.post(
        CHECKOUT_URL,
        checkout_payload(shipping_provider_code="UPS"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert response.data["errors"]["shipping_provider_code"] == ["Unknown shipping provider."]


@pytest.mark.django_db
def test_checkout_rejects_invalid_service_code_for_provider(client):
    _add_product_to_cart(client)

    response = client.post(
        CHECKOUT_URL,
        checkout_payload(
            shipping_provider_code="MOCK",
            shipping_service_code="overnight",
        ),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert response.data["errors"]["shipping_service_code"] == ["Unknown shipping service for provider."]


@pytest.mark.django_db
def test_order_stores_shipping_snapshot_fields(client):
    _add_product_to_cart(client)

    response = client.post(
        CHECKOUT_URL,
        checkout_payload(
            shipping_provider_code="MOCK",
            shipping_service_code="express",
        ),
        format="json",
    )

    assert response.status_code == 201
    order = Order.objects.get(pk=response.data["id"])
    assert order.shipping_provider_code == "MOCK"
    assert order.shipping_service_code == "express"
    assert order.shipping_method_name == "Express"


@pytest.mark.django_db
def test_order_detail_exposes_shipping_method_summary(auth_client, user):
    _add_product_to_cart(auth_client)

    checkout_response = auth_client.post(
        CHECKOUT_URL,
        checkout_payload(
            customer_email=user.email,
            shipping_provider_code="MOCK",
            shipping_service_code="standard",
        ),
        format="json",
    )

    assert checkout_response.status_code == 201

    order_response = auth_client.get(f"/api/v1/orders/{checkout_response.data['id']}/")
    assert order_response.status_code == 200
    assert order_response.data["shipping_method"] == {
        "provider_code": "MOCK",
        "service_code": "standard",
        "name": "Standard",
    }


@pytest.mark.django_db
def test_order_detail_exposes_latest_shipment_summary(auth_client, user):
    order = Order.objects.create(
        user=user,
        status=Order.Status.SHIPPED,
        customer_email=user.email,
        shipping_first_name="Test",
        shipping_last_name="User",
        shipping_address_line1="Main Street 1",
        shipping_city="Prague",
        shipping_postal_code="11000",
        shipping_country="CZ",
        shipping_phone="+420123456789",
        shipping_provider_code="MOCK",
        shipping_service_code="express",
        shipping_method_name="Express",
        billing_same_as_shipping=True,
    )
    order.shipments.create(
        provider_code="MOCK",
        service_code="express",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Express",
        tracking_number="MOCK-123-EXPRESS",
        status=ShipmentStatus.IN_TRANSIT,
        label_url="https://mock-shipping.local/labels/MOCK-123-EXPRESS",
        receiver_snapshot={"name": "Test User"},
    )

    response = auth_client.get(f"/api/v1/orders/{order.id}/")

    assert response.status_code == 200
    assert response.data["shipping_method"] == {
        "provider_code": "MOCK",
        "service_code": "express",
        "name": "Express",
    }
    assert response.data["shipment_summary"] == {
        "status": ShipmentStatus.IN_TRANSIT,
        "tracking_number": "MOCK-123-EXPRESS",
        "label_url": "https://mock-shipping.local/labels/MOCK-123-EXPRESS",
    }