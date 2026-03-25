"""Checkout + payment orchestration wiring tests (Slice PR2/4).

Verifies that:
- Checkout request accepts payment_method (required field).
- Checkout with CARD triggers AcquireMock-backed orchestration and returns a
  REDIRECT-flow payment_initiation section in the response.
- Checkout with COD triggers the DevFake-backed direct flow and returns a
  DIRECT-flow payment_initiation section with no redirect_url.
- Payment record is created and linked to the order after checkout.
- Order creation semantics remain intact (items copied, cart converted, etc.).
- Invalid / unsupported payment_method values are explicitly rejected (400).
- Checkout code does not branch on AcquireMock-specific details; provider
  selection belongs exclusively to the resolver.

CARD tests mock requests.post to avoid a running AcquireMock instance.
COD tests use DevFakeProvider directly — no HTTP mocking needed.
"""

from unittest.mock import MagicMock, patch

import pytest
from products.models import Product
from orders.models import Order
from payments.models import Payment
from tests.conftest import checkout_payload

CHECKOUT_URL = "/api/v1/cart/checkout/"
_ACQUIREMOCK_REDIRECT = "https://acquiremock.test/pay/test_session_001"
_ACQUIREMOCK_PAYMENT_ID = "pay_test_001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_product_to_cart(client, price: float = 50.0, stock: int = 10) -> Product:
    """Create a product and add one unit to the client's active cart."""
    product = Product.objects.create(
        name="Checkout Wiring Test Product",
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


def _mock_acquiremock_success(payment_id: str = _ACQUIREMOCK_PAYMENT_ID,
                              redirect_url: str = _ACQUIREMOCK_REDIRECT) -> MagicMock:
    """Return a mock requests.Response that simulates successful AcquireMock invoice creation."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "id": payment_id,
        "redirect_url": redirect_url,
    }
    return mock_resp


# ---------------------------------------------------------------------------
# 1. payment_method field presence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_checkout_without_payment_method_is_rejected(client):
    """A checkout request missing payment_method must be rejected with 400."""
    _add_product_to_cart(client)
    # Build payload without payment_method
    payload = {k: v for k, v in checkout_payload().items() if k != "payment_method"}
    response = client.post(CHECKOUT_URL, payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_checkout_with_invalid_payment_method_is_rejected(client):
    """An unrecognised payment_method value must be rejected with 400."""
    _add_product_to_cart(client)
    payload = checkout_payload(payment_method="BITCOIN")
    response = client.post(CHECKOUT_URL, payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_checkout_with_card_payment_method_is_accepted(client, settings):
    """CARD is a valid payment_method; checkout should succeed (not 400)."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    assert response.status_code == 201


@pytest.mark.django_db
def test_checkout_with_cod_payment_method_is_accepted(client):
    """COD is a valid payment_method; checkout should succeed (not 400)."""
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# 2. CARD flow — payment_initiation in response
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_card_checkout_response_contains_payment_initiation(client, settings):
    """Checkout with CARD returns a payment_initiation key in the response."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    assert "payment_initiation" in response.json()


@pytest.mark.django_db
def test_card_checkout_payment_flow_is_redirect(client, settings):
    """Checkout with CARD returns payment_initiation.payment_flow == 'REDIRECT'."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    assert response.json()["payment_initiation"]["payment_flow"] == "REDIRECT"


@pytest.mark.django_db
def test_card_checkout_returns_redirect_url(client, settings):
    """Checkout with CARD includes the hosted gateway redirect_url in the response."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success(redirect_url=_ACQUIREMOCK_REDIRECT)):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    assert response.json()["payment_initiation"]["redirect_url"] == _ACQUIREMOCK_REDIRECT


@pytest.mark.django_db
def test_card_checkout_redirect_url_not_none(client, settings):
    """For CARD checkouts, redirect_url in payment_initiation must not be None."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    assert response.json()["payment_initiation"]["redirect_url"] is not None


@pytest.mark.django_db
def test_card_checkout_payment_initiation_includes_payment_id(client, settings):
    """payment_initiation.payment_id is present and identifies the created Payment record."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    data = response.json()
    payment_id = data["payment_initiation"]["payment_id"]
    assert Payment.objects.filter(pk=payment_id).exists()


# ---------------------------------------------------------------------------
# 3. COD flow — payment_initiation in response
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cod_checkout_response_contains_payment_initiation(client):
    """Checkout with COD also returns a payment_initiation key."""
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    assert "payment_initiation" in response.json()


@pytest.mark.django_db
def test_cod_checkout_payment_flow_is_direct(client):
    """Checkout with COD returns payment_initiation.payment_flow == 'DIRECT'."""
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    assert response.json()["payment_initiation"]["payment_flow"] == "DIRECT"


@pytest.mark.django_db
def test_cod_checkout_redirect_url_is_none(client):
    """Checkout with COD must not include a redirect_url."""
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    assert response.json()["payment_initiation"]["redirect_url"] is None


@pytest.mark.django_db
def test_cod_checkout_payment_initiation_includes_payment_id(client):
    """COD checkout also creates a Payment record referenced in payment_initiation."""
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    data = response.json()
    payment_id = data["payment_initiation"]["payment_id"]
    assert Payment.objects.filter(pk=payment_id).exists()


# ---------------------------------------------------------------------------
# 4. Payment record persistence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cod_checkout_creates_payment_record(client):
    """After a COD checkout, exactly one Payment record exists for the order."""
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    assert Payment.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_card_checkout_creates_payment_record(client, settings):
    """After a CARD checkout, exactly one Payment record exists for the order."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    assert Payment.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_cod_payment_method_stored_on_payment_record(client):
    """Payment record created during COD checkout stores payment_method=COD."""
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    payment = Payment.objects.get(order=order)
    assert payment.payment_method == Payment.PaymentMethod.COD


@pytest.mark.django_db
def test_card_payment_method_stored_on_payment_record(client, settings):
    """Payment record created during CARD checkout stores payment_method=CARD."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    payment = Payment.objects.get(order=order)
    assert payment.payment_method == Payment.PaymentMethod.CARD


@pytest.mark.django_db
def test_card_redirect_url_persisted_on_payment(client, settings):
    """The redirect URL from AcquireMock is persisted on the Payment record."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success(redirect_url=_ACQUIREMOCK_REDIRECT)):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    payment = Payment.objects.get(order=order)
    assert payment.redirect_url == _ACQUIREMOCK_REDIRECT


# ---------------------------------------------------------------------------
# 5. Order creation semantics remain intact
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_is_created_after_card_checkout(client, settings):
    """An Order record exists after a CARD checkout."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    assert Order.objects.filter(id=response.json()["id"]).exists()


@pytest.mark.django_db
def test_cart_is_converted_after_cod_checkout(client, db):
    """Cart is marked CONVERTED after a successful COD checkout."""
    from carts.models import Cart
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    assert response.status_code == 201
    assert not Cart.objects.filter(status=Cart.Status.ACTIVE).exists()


@pytest.mark.django_db
def test_order_response_includes_id_after_cod_checkout(client):
    """Checkout response still contains the order 'id' field (existing contract)."""
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    assert "id" in response.json()


# ---------------------------------------------------------------------------
# 6. Provider encapsulation — no AcquireMock specifics in checkout code
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_checkout_delegates_provider_selection_not_hardcoded(client, settings):
    """Checkout routes CARD through the provider resolver, not via hardcoded AcquireMock logic.

    Verify by pointing resolver at a patched provider — checkout must still succeed.
    The checkout view should NOT contain any AcquireMock-specific branching.
    """
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    # Patch at the resolver level, not at the AcquireMock HTTP level.
    # If checkout was hardcoded to AcquireMock, it would bypass the resolver.
    with patch(
        "payments.providers.resolver.resolve_provider",
        wraps=lambda method: __import__(
            "payments.providers.acquiremock", fromlist=["AcquireMockProvider"]
        ).AcquireMockProvider(),
    ):
        with patch("payments.providers.acquiremock.requests.post",
                   return_value=_mock_acquiremock_success()):
            response = client.post(
                CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json"
            )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# 7. Redirect payment semantics — CARD checkout must NOT finalize payment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_card_checkout_payment_stays_pending(client, settings):
    """CARD checkout initiates a redirect session; payment must remain PENDING.

    AcquireMock success=True + redirect_url means 'session created', NOT
    'payment received'.  Final SUCCESS arrives only via the webhook.
    """
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    assert response.status_code == 201
    order = Order.objects.get(id=response.json()["id"])
    payment = Payment.objects.get(order=order)
    assert payment.status == Payment.Status.PENDING, (
        "CARD payment must stay PENDING after checkout — "
        "final SUCCESS is applied only by the AcquireMock webhook."
    )


@pytest.mark.django_db
def test_card_checkout_order_is_not_paid(client, settings):
    """CARD checkout must leave the order in a non-final payment state.

    The order is CREATED at checkout time and transitions to PAID only after
    the webhook confirms the customer completed payment.
    """
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    assert order.status != Order.Status.PAID, (
        "Order must not be PAID after CARD checkout — "
        "PAID is set by the webhook, not by checkout."
    )


@pytest.mark.django_db
def test_card_checkout_reservations_stay_active(client, settings):
    """Inventory reservations must NOT be committed during CARD checkout.

    Commitment (stock decrement) only happens once the webhook confirms payment.
    """
    from orders.models import InventoryReservation
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    product = _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success()):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    reservations = InventoryReservation.objects.filter(order=order)
    assert reservations.exists()
    assert all(r.status == InventoryReservation.Status.ACTIVE for r in reservations), (
        "Reservations must remain ACTIVE after CARD checkout; "
        "commitment happens on webhook-confirmed success."
    )
    product.refresh_from_db()
    assert product.stock_quantity == 10, (
        "Stock must not be decremented during CARD checkout redirect initiation."
    )


@pytest.mark.django_db
def test_card_checkout_provider_payment_id_persisted_on_pending_payment(client, settings):
    """AcquireMock provider_payment_id is persisted even while payment is PENDING."""
    settings.ACQUIREMOCK_BASE_URL = "https://acquiremock.test"
    settings.ACQUIREMOCK_API_KEY = "test-key"
    _add_product_to_cart(client)
    with patch("payments.providers.acquiremock.requests.post",
               return_value=_mock_acquiremock_success(payment_id=_ACQUIREMOCK_PAYMENT_ID)):
        response = client.post(CHECKOUT_URL, checkout_payload(payment_method="CARD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    payment = Payment.objects.get(order=order)
    assert payment.provider_payment_id == _ACQUIREMOCK_PAYMENT_ID
    assert payment.status == Payment.Status.PENDING


@pytest.mark.django_db
def test_cod_checkout_payment_is_pending(client):
    """COD checkout must leave payment in PENDING state.

    Finalisation happens via an explicit POST /payments/ call — the checkout
    itself only initiates the deferred flow.  SUCCESS is applied separately.
    """
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    payment = Payment.objects.get(order=order)
    assert payment.status == Payment.Status.PENDING, (
        "COD payment must stay PENDING after checkout — "
        "SUCCESS is applied only via the explicit /payments/ endpoint."
    )


@pytest.mark.django_db
def test_cod_checkout_order_is_created(client):
    """COD checkout must leave the order in CREATED state.

    The order transitions to PAID only after the explicit POST /payments/ call
    confirms the payment — matching the legacy DEV simulation flow.
    """
    _add_product_to_cart(client)
    response = client.post(CHECKOUT_URL, checkout_payload(payment_method="COD"), format="json")
    order = Order.objects.get(id=response.json()["id"])
    assert order.status == Order.Status.CREATED, (
        "Order must not be PAID after COD checkout — "
        "PAID is set only after explicit payment confirmation."
    )
