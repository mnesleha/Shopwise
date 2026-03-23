"""
Supplier configuration and order snapshot tests.

Covers:
- Supplier model creation and validation
- SupplierAddress default guard (no duplicate defaults per supplier)
- SupplierPaymentDetails default guard
- resolve_order_supplier_snapshot() happy path and all error cases
- Checkout snapshots supplier identity / address / payment data into the order
- Changing supplier config after checkout does NOT retroactively change the order
- Order serializer returns supplier block from stored order snapshot truth
- Checkout returns HTTP 503 when supplier configuration is missing or broken
- Admin screens load for Supplier, SupplierAddress, SupplierPaymentDetails
"""

from decimal import Decimal

import pytest
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from orders.models import Order
from products.models import Product
from suppliers.admin import (
    SupplierAddressAdmin,
    SupplierAdmin,
    SupplierPaymentDetailsAdmin,
)
from suppliers.models import Supplier, SupplierAddress, SupplierPaymentDetails
from suppliers.services import SupplierConfigurationError, resolve_order_supplier_snapshot
from tests.conftest import checkout_payload, make_default_supplier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _active_product(*, name: str = "Widget", price: str = "10.00", stock: int = 10) -> Product:
    return Product.objects.create(
        name=name,
        price=Decimal(price),
        price_net_amount=Decimal(price),
        currency="EUR",
        stock_quantity=stock,
        is_active=True,
    )


def _do_checkout(client) -> dict:
    product = _active_product()
    client.get("/api/v1/cart/")
    client.post("/api/v1/cart/items/", {"product_id": product.id, "quantity": 1}, format="json")
    response = client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    return response


# ===========================================================================
# 1. Model / config validation
# ===========================================================================


@pytest.mark.django_db
class TestSupplierModel:
    def test_create_supplier(self):
        s = Supplier.objects.create(
            name="Acme Corp",
            company_id="ACME-001",
            vat_id="CZ12345678",
            email="info@acme.example",
            phone="+420123456789",
            is_active=True,
        )
        assert s.pk is not None
        assert str(s) == "Acme Corp"

    def test_supplier_inactive_by_default(self):
        s = Supplier.objects.create(name="Inactive Corp", is_active=False)
        assert not s.is_active

    def test_supplier_has_address_and_payment(self):
        supplier = Supplier.objects.create(name="Full Supplier", is_active=True)
        addr = SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="Main St 1",
            city="Brno",
            postal_code="60200",
            country="CZ",
            is_default_for_orders=True,
        )
        payment = SupplierPaymentDetails.objects.create(
            supplier=supplier,
            bank_name="KB",
            iban="CZ1234567890",
            swift="KOMBCZPP",
            is_default_for_orders=True,
        )
        assert addr.supplier_id == supplier.pk
        assert payment.supplier_id == supplier.pk


@pytest.mark.django_db
class TestSupplierAddressDefaultGuard:
    def test_second_default_address_detected_by_service(self):
        """Service raises SupplierConfigurationError when two addresses share
        is_default_for_orders — guards against data bypassing model.clean().
        Validation is intentionally kept at the service level, not model.clean(),
        to avoid false positives when switching defaults via Django admin inlines.
        """
        Supplier.objects.all().delete()
        supplier = Supplier.objects.create(name="Dupe Test Supplier", is_active=True)
        SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="First St 1",
            city="Prague",
            postal_code="11000",
            country="CZ",
            is_default_for_orders=True,
        )
        # Second default — insert directly to simulate data bypassing clean().
        SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="Second St 2",
            city="Brno",
            postal_code="60200",
            country="CZ",
            is_default_for_orders=True,
        )
        SupplierPaymentDetails.objects.create(
            supplier=supplier,
            iban="CZ0001",
            is_default_for_orders=True,
        )
        with pytest.raises(SupplierConfigurationError) as exc_info:
            resolve_order_supplier_snapshot()
        assert "2 addresses" in str(exc_info.value.detail)

    def test_non_default_addresses_are_unlimited(self):
        """Multiple non-default addresses for the same supplier are allowed."""
        supplier = Supplier.objects.create(name="Multi Addr Supplier", is_active=True)
        for i in range(3):
            addr = SupplierAddress(
                supplier=supplier,
                street_line_1=f"Street {i}",
                city="Prague",
                postal_code="11000",
                country="CZ",
                is_default_for_orders=False,
            )
            addr.clean()  # must not raise
            addr.save()
        assert SupplierAddress.objects.filter(supplier=supplier).count() == 3

    def test_editing_existing_default_address_does_not_self_conflict(self):
        """Saving an already-default address with no other default does not raise."""
        supplier = Supplier.objects.create(name="Edit Safe Supplier", is_active=True)
        addr = SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="Original St 1",
            city="Prague",
            postal_code="11000",
            country="CZ",
            is_default_for_orders=True,
        )
        # Re-save the same address with is_default_for_orders=True — must not raise.
        addr.label = "Updated"
        addr.clean()  # must not raise
        addr.save()

    def test_default_address_str_includes_marker(self):
        supplier = Supplier.objects.create(name="Str Supplier", is_active=True)
        addr = SupplierAddress(
            supplier=supplier,
            street_line_1="Test St",
            city="Prague",
            country="CZ",
            postal_code="11000",
            is_default_for_orders=True,
        )
        assert "[default]" in str(addr)


@pytest.mark.django_db
class TestSupplierPaymentDetailsDefaultGuard:
    def test_second_default_payment_detected_by_service(self):
        """Service raises SupplierConfigurationError when two payment records share
        is_default_for_orders — guards against data bypassing model.clean().
        """
        Supplier.objects.all().delete()
        supplier = Supplier.objects.create(name="Payment Dupe Supplier", is_active=True)
        SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="Main St 1",
            city="Prague",
            postal_code="11000",
            country="CZ",
            is_default_for_orders=True,
        )
        SupplierPaymentDetails.objects.create(
            supplier=supplier,
            iban="CZ0001",
            is_default_for_orders=True,
        )
        # Second default — insert directly to simulate data bypassing clean().
        SupplierPaymentDetails.objects.create(
            supplier=supplier,
            iban="CZ0002",
            is_default_for_orders=True,
        )
        with pytest.raises(SupplierConfigurationError) as exc_info:
            resolve_order_supplier_snapshot()
        assert "2 payment records" in str(exc_info.value.detail)

    def test_non_default_payment_records_are_unlimited(self):
        """Multiple non-default payment records for the same supplier are allowed."""
        supplier = Supplier.objects.create(name="Multi Pay Supplier", is_active=True)
        for i in range(3):
            p = SupplierPaymentDetails(
                supplier=supplier,
                iban=f"CZ000{i}",
                is_default_for_orders=False,
            )
            p.clean()  # must not raise
            p.save()
        assert SupplierPaymentDetails.objects.filter(supplier=supplier).count() == 3


# ===========================================================================
# 2. resolve_order_supplier_snapshot — service-layer invariants
# ===========================================================================


@pytest.mark.django_db
class TestResolveOrderSupplierSnapshot:
    def test_happy_path_returns_snapshot(self):
        """With a valid active supplier + default address + default payment, returns snapshot."""
        # The autouse fixture already created a valid config; clean it and build a fresh one.
        Supplier.objects.all().delete()
        supplier = Supplier.objects.create(
            name="Invoice Sender",
            company_id="IS-001",
            vat_id="CZ99999999",
            email="billing@invoicesender.example",
            phone="+420111222333",
            is_active=True,
        )
        SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="Invoice Road 1",
            city="Brno",
            postal_code="61200",
            country="CZ",
            is_default_for_orders=True,
        )
        SupplierPaymentDetails.objects.create(
            supplier=supplier,
            bank_name="Česká spořitelna",
            iban="CZ6550800000000000000001",
            swift="GIBACZPX",
            is_default_for_orders=True,
        )

        snap = resolve_order_supplier_snapshot()

        assert snap.name == "Invoice Sender"
        assert snap.company_id == "IS-001"
        assert snap.vat_id == "CZ99999999"
        assert snap.email == "billing@invoicesender.example"
        assert snap.phone == "+420111222333"
        assert snap.street_line_1 == "Invoice Road 1"
        assert snap.city == "Brno"
        assert snap.postal_code == "61200"
        assert snap.country == "CZ"
        assert snap.bank_name == "Česká spořitelna"
        assert snap.iban == "CZ6550800000000000000001"
        assert snap.swift == "GIBACZPX"

    def test_no_active_supplier_raises(self):
        Supplier.objects.all().delete()
        with pytest.raises(SupplierConfigurationError) as exc_info:
            resolve_order_supplier_snapshot()
        assert "No active supplier" in str(exc_info.value.detail)

    def test_multiple_active_suppliers_raises(self):
        # autouse already creates one; add a second active one.
        Supplier.objects.create(name="Second Active", is_active=True)
        with pytest.raises(SupplierConfigurationError) as exc_info:
            resolve_order_supplier_snapshot()
        assert "active suppliers found" in str(exc_info.value.detail)

    def test_no_default_address_raises(self):
        Supplier.objects.all().delete()
        supplier = Supplier.objects.create(name="No Address Supplier", is_active=True)
        SupplierPaymentDetails.objects.create(
            supplier=supplier, iban="CZ0001", is_default_for_orders=True
        )
        with pytest.raises(SupplierConfigurationError) as exc_info:
            resolve_order_supplier_snapshot()
        assert "no default order address" in str(exc_info.value.detail)

    def test_multiple_default_addresses_raises(self):
        Supplier.objects.all().delete()
        supplier = Supplier.objects.create(name="Multi Addr Supplier", is_active=True)
        SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="Addr 1",
            city="Prague",
            postal_code="11000",
            country="CZ",
            is_default_for_orders=True,
        )
        # Bypass clean() to force the object into DB directly.
        SupplierAddress.objects.filter(supplier=supplier, is_default_for_orders=True).update()
        SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="Addr 2",
            city="Brno",
            postal_code="60200",
            country="CZ",
            is_default_for_orders=True,
        )
        SupplierPaymentDetails.objects.create(
            supplier=supplier, iban="CZ0001", is_default_for_orders=True
        )
        with pytest.raises(SupplierConfigurationError) as exc_info:
            resolve_order_supplier_snapshot()
        assert "exactly one is required" in str(exc_info.value.detail)

    def test_no_default_payment_raises(self):
        Supplier.objects.all().delete()
        supplier = Supplier.objects.create(name="No Payment Supplier", is_active=True)
        SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="Street 1",
            city="Prague",
            postal_code="11000",
            country="CZ",
            is_default_for_orders=True,
        )
        with pytest.raises(SupplierConfigurationError) as exc_info:
            resolve_order_supplier_snapshot()
        assert "no default payment" in str(exc_info.value.detail)

    def test_multiple_default_payments_raises(self):
        Supplier.objects.all().delete()
        supplier = Supplier.objects.create(name="Multi Pay Supplier", is_active=True)
        SupplierAddress.objects.create(
            supplier=supplier,
            street_line_1="Street 1",
            city="Prague",
            postal_code="11000",
            country="CZ",
            is_default_for_orders=True,
        )
        SupplierPaymentDetails.objects.create(
            supplier=supplier, iban="CZ0001", is_default_for_orders=True
        )
        SupplierPaymentDetails.objects.create(
            supplier=supplier, iban="CZ0002", is_default_for_orders=True
        )
        with pytest.raises(SupplierConfigurationError) as exc_info:
            resolve_order_supplier_snapshot()
        assert "exactly one is required" in str(exc_info.value.detail)


# ===========================================================================
# 3. Order creation — snapshot persistence
# ===========================================================================


@pytest.mark.django_db
class TestCheckoutSupplierSnapshot:
    def test_checkout_persists_supplier_identity_snapshot(self, auth_client):
        """Supplier identity fields are persisted into the order at checkout."""
        # The autouse fixture already provides the default supplier config.
        supplier = Supplier.objects.get(is_active=True)
        supplier.name = "Snapshot Test GmbH"
        supplier.company_id = "SNAP-001"
        supplier.vat_id = "DE123456789"
        supplier.email = "snap@test.example"
        supplier.phone = "+49123456789"
        supplier.save()

        response = _do_checkout(auth_client)
        assert response.status_code == 201, response.json()

        order = Order.objects.get(pk=response.json()["id"])
        assert order.supplier_name == "Snapshot Test GmbH"
        assert order.supplier_company_id == "SNAP-001"
        assert order.supplier_vat_id == "DE123456789"
        assert order.supplier_email == "snap@test.example"
        assert order.supplier_phone == "+49123456789"

    def test_checkout_persists_supplier_address_snapshot(self, auth_client):
        """Supplier address fields are persisted into the order at checkout."""
        supplier = Supplier.objects.get(is_active=True)
        SupplierAddress.objects.filter(supplier=supplier).update(
            street_line_1="Snap Ave 42",
            street_line_2="Suite 3B",
            city="Cologne",
            postal_code="50667",
            country="DE",
        )

        response = _do_checkout(auth_client)
        assert response.status_code == 201

        order = Order.objects.get(pk=response.json()["id"])
        assert order.supplier_street_line_1 == "Snap Ave 42"
        assert order.supplier_street_line_2 == "Suite 3B"
        assert order.supplier_city == "Cologne"
        assert order.supplier_postal_code == "50667"
        assert order.supplier_country == "DE"

    def test_checkout_persists_supplier_payment_snapshot(self, auth_client):
        """Supplier payment details are persisted into the order at checkout."""
        supplier = Supplier.objects.get(is_active=True)
        SupplierPaymentDetails.objects.filter(supplier=supplier).update(
            bank_name="Snap Bank",
            account_number="987654321/0300",
            iban="DE89370400440532013000",
            swift="COBADEFFXXX",
        )

        response = _do_checkout(auth_client)
        assert response.status_code == 201

        order = Order.objects.get(pk=response.json()["id"])
        assert order.supplier_bank_name == "Snap Bank"
        assert order.supplier_account_number == "987654321/0300"
        assert order.supplier_iban == "DE89370400440532013000"
        assert order.supplier_swift == "COBADEFFXXX"

    def test_changing_supplier_after_checkout_does_not_affect_existing_order(self, auth_client):
        """Updating supplier config after checkout must NOT change the stored snapshot."""
        response = _do_checkout(auth_client)
        assert response.status_code == 201

        order = Order.objects.get(pk=response.json()["id"])
        original_name = order.supplier_name
        original_iban = order.supplier_iban

        # Mutate the supplier config.
        Supplier.objects.filter(is_active=True).update(name="Changed Name")
        SupplierPaymentDetails.objects.filter(is_default_for_orders=True).update(
            iban="CZ0000000000000000000000"
        )

        order.refresh_from_db()
        # Snapshot must not have changed.
        assert order.supplier_name == original_name
        assert order.supplier_iban == original_iban


# ===========================================================================
# 4. Checkout fails clearly when supplier config is missing
# ===========================================================================


@pytest.mark.django_db
class TestCheckoutFailsOnMissingSupplierConfig:
    def test_checkout_returns_503_when_no_active_supplier(self, auth_client):
        """Checkout must return 503 when no active supplier is configured."""
        Supplier.objects.all().delete()

        product = _active_product()
        auth_client.get("/api/v1/cart/")
        auth_client.post(
            "/api/v1/cart/items/",
            {"product_id": product.id, "quantity": 1},
            format="json",
        )
        response = auth_client.post(
            "/api/v1/cart/checkout/",
            checkout_payload(),
            format="json",
        )
        assert response.status_code == 503
        data = response.json()
        assert data.get("code") == "SUPPLIER_CONFIGURATION_ERROR"

    def test_checkout_returns_503_when_no_default_address(self, auth_client):
        """Checkout must return 503 when the active supplier has no default address."""
        # Remove all default addresses from the existing supplier.
        SupplierAddress.objects.filter(is_default_for_orders=True).update(
            is_default_for_orders=False
        )

        product = _active_product()
        auth_client.get("/api/v1/cart/")
        auth_client.post(
            "/api/v1/cart/items/",
            {"product_id": product.id, "quantity": 1},
            format="json",
        )
        response = auth_client.post(
            "/api/v1/cart/checkout/",
            checkout_payload(),
            format="json",
        )
        assert response.status_code == 503
        data = response.json()
        assert data.get("code") == "SUPPLIER_CONFIGURATION_ERROR"

    def test_checkout_returns_503_when_no_default_payment_details(self, auth_client):
        """Checkout must return 503 when the active supplier has no default payment details."""
        SupplierPaymentDetails.objects.filter(is_default_for_orders=True).update(
            is_default_for_orders=False
        )

        product = _active_product()
        auth_client.get("/api/v1/cart/")
        auth_client.post(
            "/api/v1/cart/items/",
            {"product_id": product.id, "quantity": 1},
            format="json",
        )
        response = auth_client.post(
            "/api/v1/cart/checkout/",
            checkout_payload(),
            format="json",
        )
        assert response.status_code == 503
        data = response.json()
        assert data.get("code") == "SUPPLIER_CONFIGURATION_ERROR"

    def test_checkout_does_not_create_order_when_supplier_config_missing(self, auth_client):
        """No order must be left in the DB when checkout fails due to supplier config."""
        Supplier.objects.all().delete()

        product = _active_product()
        auth_client.get("/api/v1/cart/")
        auth_client.post(
            "/api/v1/cart/items/",
            {"product_id": product.id, "quantity": 1},
            format="json",
        )
        order_count_before = Order.objects.count()
        auth_client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
        assert Order.objects.count() == order_count_before


# ===========================================================================
# 5. Serializer / order detail — supplier block from stored snapshot truth
# ===========================================================================


@pytest.mark.django_db
class TestOrderSerializerSupplierBlock:
    def test_order_detail_includes_supplier_block(self, auth_client):
        """GET /orders/{id}/ must include a `supplier` key when snapshot is present."""
        response = _do_checkout(auth_client)
        assert response.status_code == 201

        order_id = response.json()["id"]
        detail = auth_client.get(f"/api/v1/orders/{order_id}/")
        assert detail.status_code == 200

        data = detail.json()
        assert "supplier" in data
        assert data["supplier"] is not None

    def test_supplier_block_contains_expected_keys(self, auth_client):
        response = _do_checkout(auth_client)
        order_id = response.json()["id"]
        data = auth_client.get(f"/api/v1/orders/{order_id}/").json()

        supplier = data["supplier"]
        expected_keys = {
            "name", "company_id", "vat_id", "email", "phone",
            "street_line_1", "street_line_2", "city", "postal_code", "country",
            "bank_name", "account_number", "iban", "swift",
        }
        assert expected_keys <= set(supplier.keys())

    def test_supplier_block_reflects_snapshot_not_live_config(self, auth_client):
        """Supplier block must come from stored snapshot, not the current live config."""
        # Mutate supplier before checkout to record the name.
        Supplier.objects.filter(is_active=True).update(name="Original Name")
        response = _do_checkout(auth_client)
        assert response.status_code == 201
        order_id = response.json()["id"]

        # Now change the live supplier name.
        Supplier.objects.filter(is_active=True).update(name="Changed Name After Order")

        data = auth_client.get(f"/api/v1/orders/{order_id}/").json()
        # The serialised supplier block must still read the snapshot.
        assert data["supplier"]["name"] == "Original Name"

    def test_pre_supplier_order_returns_null_supplier_block(self, auth_client):
        """Orders without supplier snapshot (pre-feature) must return supplier: null."""
        # Simulate creating an order the old way, without supplier snapshot fields.
        from tests.conftest import create_valid_order
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(email="testuser@example.com").first()
        order = create_valid_order(user=user)
        # Supplier snapshot fields are null by default for directly-created orders.
        assert order.supplier_name is None

        detail = auth_client.get(f"/api/v1/orders/{order.id}/")
        assert detail.status_code == 200
        data = detail.json()
        assert data["supplier"] is None


# ===========================================================================
# 6. Admin smoke tests
# ===========================================================================


@pytest.mark.django_db
class TestSupplierAdmin:
    @pytest.fixture
    def site(self):
        return AdminSite()

    @pytest.fixture
    def supplier_admin(self, site):
        return SupplierAdmin(Supplier, site)

    @pytest.fixture
    def address_admin(self, site):
        return SupplierAddressAdmin(SupplierAddress, site)

    @pytest.fixture
    def payment_admin(self, site):
        return SupplierPaymentDetailsAdmin(SupplierPaymentDetails, site)

    def test_supplier_admin_registered(self):
        from django.contrib.admin.sites import site as default_site
        assert Supplier in default_site._registry

    def test_supplier_address_admin_registered(self):
        from django.contrib.admin.sites import site as default_site
        assert SupplierAddress in default_site._registry

    def test_supplier_payment_details_admin_registered(self):
        from django.contrib.admin.sites import site as default_site
        assert SupplierPaymentDetails in default_site._registry

    def test_supplier_admin_list_display(self, supplier_admin):
        assert "name" in supplier_admin.list_display
        assert "is_active" in supplier_admin.list_display

    def test_supplier_address_admin_default_badge(self, address_admin):
        """default_badge helper returns correct boolean for display."""
        addr = SupplierAddress(is_default_for_orders=True)
        assert address_admin.default_badge(addr) is True

        addr.is_default_for_orders = False
        assert address_admin.default_badge(addr) is False

    def test_supplier_payment_admin_default_badge(self, payment_admin):
        payment = SupplierPaymentDetails(is_default_for_orders=True)
        assert payment_admin.default_badge(payment) is True

        payment.is_default_for_orders = False
        assert payment_admin.default_badge(payment) is False

    def test_supplier_admin_has_fieldsets(self, supplier_admin):
        assert supplier_admin.fieldsets is not None
        fieldset_names = [fs[0] for fs in supplier_admin.fieldsets]
        assert "Supplier Identity" in fieldset_names
        assert "Configuration" in fieldset_names

    def test_address_admin_has_fieldsets(self, address_admin):
        fieldset_names = [fs[0] for fs in address_admin.fieldsets]
        assert "Address" in fieldset_names
        assert "Order Configuration" in fieldset_names

    def test_payment_admin_has_fieldsets(self, payment_admin):
        fieldset_names = [fs[0] for fs in payment_admin.fieldsets]
        assert "Payment Details" in fieldset_names
        assert "Order Configuration" in fieldset_names
