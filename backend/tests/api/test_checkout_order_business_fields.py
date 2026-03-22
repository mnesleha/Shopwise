"""
Tests verifying that business address fields (company, company_id, vat_id)
are persisted in the Order shipping/billing snapshot after checkout, and are
exposed correctly via OrderResponseSerializer.
"""

import pytest
from products.models import Product
from orders.models import Order
from tests.conftest import checkout_payload


def _add_product_to_cart(client, price=100, stock=10):
    product = Product.objects.create(
        name="Test Product",
        price=price,
        stock_quantity=stock,
        is_active=True,
    )
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    return product


# ---------------------------------------------------------------------------
# Shipping business fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_stores_shipping_company_fields(client):
    """
    After checkout, Order.shipping_company / shipping_company_id / shipping_vat_id
    must reflect the submitted values.
    """
    _add_product_to_cart(client)

    payload = checkout_payload(
        shipping_company="Acme Corp",
        shipping_company_id="CRN-2024",
        shipping_vat_id="EU123456789",
    )
    resp = client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    order = Order.objects.get(id=resp.data["id"])
    assert order.shipping_company == "Acme Corp"
    assert order.shipping_company_id == "CRN-2024"
    assert order.shipping_vat_id == "EU123456789"


@pytest.mark.django_db
def test_order_shipping_business_fields_default_null(client):
    """
    When no business fields are supplied at checkout the order shipping
    business fields must be NULL (not empty string).
    """
    _add_product_to_cart(client)

    resp = client.post(
        "/api/v1/cart/checkout/", checkout_payload(), format="json"
    )

    assert resp.status_code == 201
    order = Order.objects.get(id=resp.data["id"])
    assert order.shipping_company is None
    assert order.shipping_company_id is None
    assert order.shipping_vat_id is None


# ---------------------------------------------------------------------------
# Billing business fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_stores_billing_company_fields(client):
    """
    When billing_same_as_shipping=False and billing business fields are
    supplied, they are captured on the Order row.
    """
    _add_product_to_cart(client)

    payload = checkout_payload(
        billing_same_as_shipping=False,
        billing_first_name="Corp",
        billing_last_name="User",
        billing_address_line1="1 Business Park",
        billing_address_line2="",
        billing_city="Commerce City",
        billing_postal_code="55555",
        billing_country="US",
        billing_phone="+10000000055",
        billing_company="BigCo Ltd",
        billing_company_id="CRN-999",
        billing_vat_id="EU987654321",
    )
    resp = client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    order = Order.objects.get(id=resp.data["id"])
    assert order.billing_company == "BigCo Ltd"
    assert order.billing_company_id == "CRN-999"
    assert order.billing_vat_id == "EU987654321"


@pytest.mark.django_db
def test_order_billing_business_fields_null_when_same_as_shipping(client):
    """
    When billing_same_as_shipping=True the billing business snapshot fields
    must remain NULL (the shipping snapshot carries the data).
    """
    _add_product_to_cart(client)

    payload = checkout_payload(
        billing_same_as_shipping=True,
        shipping_company="Acme Corp",
        shipping_company_id="CRN-2024",
        shipping_vat_id="EU123",
    )
    resp = client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    order = Order.objects.get(id=resp.data["id"])
    assert order.billing_company is None
    assert order.billing_company_id is None
    assert order.billing_vat_id is None


# ---------------------------------------------------------------------------
# Serializer output (shipping_address / billing_address)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_response_shipping_address_includes_business_fields(auth_client, user):
    """
    The GET /api/v1/orders/<id>/ response must include a shipping_address dict
    that contains company, company_id, and vat_id.
    """
    _add_product_to_cart(auth_client)

    payload = checkout_payload(
        customer_email=user.email,
        shipping_company="Acme Corp",
        shipping_company_id="CRN-2024",
        shipping_vat_id="EU123456789",
    )
    checkout_resp = auth_client.post("/api/v1/cart/checkout/", payload, format="json")
    assert checkout_resp.status_code == 201

    order_id = checkout_resp.data["id"]
    resp = auth_client.get(f"/api/v1/orders/{order_id}/")
    assert resp.status_code == 200

    shipping = resp.data["shipping_address"]
    assert shipping["company"] == "Acme Corp"
    assert shipping["company_id"] == "CRN-2024"
    assert shipping["vat_id"] == "EU123456789"


@pytest.mark.django_db
def test_order_response_billing_address_none_when_same_as_shipping(auth_client, user):
    """
    billing_address in the response must be None when billing_same_as_shipping=True.
    """
    _add_product_to_cart(auth_client)

    checkout_resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email, billing_same_as_shipping=True),
        format="json",
    )
    assert checkout_resp.status_code == 201

    resp = auth_client.get(f"/api/v1/orders/{checkout_resp.data['id']}/")
    assert resp.status_code == 200
    assert resp.data["billing_address"] is None


@pytest.mark.django_db
def test_order_response_billing_address_includes_business_fields(auth_client, user):
    """
    When billing_same_as_shipping=False, billing_address in the response
    contains company, company_id, and vat_id.
    """
    _add_product_to_cart(auth_client)

    payload = checkout_payload(
        customer_email=user.email,
        billing_same_as_shipping=False,
        billing_first_name="Corp",
        billing_last_name="User",
        billing_address_line1="1 Business Park",
        billing_address_line2="",
        billing_city="Commerce City",
        billing_postal_code="55555",
        billing_country="US",
        billing_phone="+10000000055",
        billing_company="BigCo",
        billing_company_id="CRN-BILL",
        billing_vat_id="EU-BILL",
    )
    checkout_resp = auth_client.post("/api/v1/cart/checkout/", payload, format="json")
    assert checkout_resp.status_code == 201

    resp = auth_client.get(f"/api/v1/orders/{checkout_resp.data['id']}/")
    assert resp.status_code == 200

    billing = resp.data["billing_address"]
    assert billing is not None
    assert billing["company"] == "BigCo"
    assert billing["company_id"] == "CRN-BILL"
    assert billing["vat_id"] == "EU-BILL"
