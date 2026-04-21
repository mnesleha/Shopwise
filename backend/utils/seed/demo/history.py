from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from carts.models import Cart, CartItem
from carts.services.pricing import get_cart_pricing_with_order_discount
from carts.services.snapshot import get_snapshot_gross_price
from orderitems.models import OrderItem
from orders.models import InventoryReservation, Order
from orders.services.inventory_reservation_service import release_reservations, reserve_for_checkout
from payments.models import Payment
from payments.providers.acquiremock_webhook import AcquireMockWebhookEvent
from payments.services.acquiremock_webhook_processor import process_acquiremock_webhook_event
from products.models import Product
from shipping.models import Shipment
from shipping.services.events import ShipmentEventService
from shipping.statuses import ShipmentStatus
from shipping.services.selection import resolve_shipping_service_selection
from suppliers.services import resolve_order_supplier_snapshot
from utils.seed.demo.config import DEMO_HISTORY_CUSTOMER_EMAIL, DEMO_ORDER_HISTORY


WriteLine = Callable[[str], None]
MONEY_QUANTIZE = Decimal("0.01")
HISTORY_MARKER_PREFIX = "DEMO-HISTORY:"


@dataclass(frozen=True)
class DemoHistorySeedContext:
    customer: Any
    admin_user: Any
    supplier_snapshot: Any
    shipping_method_name: str


def seed_demo_order_history(write: WriteLine) -> dict[str, dict[str, Any]]:
    context = _build_context()
    cleanup_demo_order_history(customer=context.customer, write=write)

    fixtures: dict[str, dict[str, Any]] = {
        "customer_email": {
            "email": context.customer.email,
        }
    }

    for order_data in DEMO_ORDER_HISTORY:
        seeded_order = _seed_history_order(context=context, order_data=order_data)
        fixtures[order_data["key"]] = {
            "id": seeded_order.id,
            "status": seeded_order.status,
            "reference": order_data["reference"],
        }
        write(f"Seeded demo history order: {order_data['reference']} ({seeded_order.status})")

    return fixtures


def cleanup_demo_order_history(*, customer, write: WriteLine | None = None) -> None:
    writer = write or (lambda message: None)
    deleted_orders, _ = Order.objects.filter(
        user=customer,
        shipping_address_line2__startswith=HISTORY_MARKER_PREFIX,
    ).delete()
    Cart.objects.filter(user=customer).delete()
    if deleted_orders:
        writer(f"Removed existing demo order history for {customer.email}")


def _build_context() -> DemoHistorySeedContext:
    user_model = get_user_model()
    customer = user_model.objects.get(email=DEMO_HISTORY_CUSTOMER_EMAIL)
    admin_user = user_model.objects.get(email="admin@shopwise.test")
    supplier_snapshot = resolve_order_supplier_snapshot()
    shipping_service = resolve_shipping_service_selection(
        provider_code="MOCK",
        service_code="standard",
    )
    return DemoHistorySeedContext(
        customer=customer,
        admin_user=admin_user,
        supplier_snapshot=supplier_snapshot,
        shipping_method_name=shipping_service.service_name,
    )


def _seed_history_order(*, context: DemoHistorySeedContext, order_data: dict[str, Any]) -> Order:
    with transaction.atomic():
        cart = Cart.objects.create(user=context.customer, status=Cart.Status.ACTIVE)
        reservation_items: list[dict[str, int]] = []

        for item_data in order_data["products"]:
            product = Product.objects.get(slug=item_data["slug"])
            quantity = int(item_data["quantity"])
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                price_at_add_time=get_snapshot_gross_price(product),
            )
            reservation_items.append({"product_id": product.id, "quantity": quantity})

        cart_pricing = get_cart_pricing_with_order_discount(cart)
        order = _create_order_snapshot(
            context=context,
            order_data=order_data,
            cart_pricing=cart_pricing,
        )
        _create_order_items(order=order, cart_pricing=cart_pricing)
        _persist_order_totals(order=order, cart_pricing=cart_pricing)
        reserve_for_checkout(order=order, items=reservation_items)
        cart.status = Cart.Status.CONVERTED
        cart.save(update_fields=["status"])

        if order_data["cancel"] is not None:
            _cancel_seeded_order(order=order, order_data=order_data)
        else:
            _complete_card_payment(order=order, order_data=order_data)
            _apply_shipment_history(order=order, webhook_statuses=order_data["webhook_statuses"])

    cart.delete()
    order.refresh_from_db()
    return order


def _create_order_snapshot(*, context: DemoHistorySeedContext, order_data: dict[str, Any], cart_pricing) -> Order:
    supplier = context.supplier_snapshot
    order = Order(
        user=context.customer,
        customer_email=context.customer.email,
        shipping_provider_code="MOCK",
        shipping_service_code="standard",
        shipping_method_name=context.shipping_method_name,
        shipping_first_name=context.customer.first_name,
        shipping_last_name=context.customer.last_name,
        shipping_address_line1="Demo Street 10",
        shipping_address_line2=f"{HISTORY_MARKER_PREFIX}{order_data['reference']}",
        shipping_city="Prague",
        shipping_postal_code="11000",
        shipping_country="CZ",
        shipping_phone="+420601234567",
        billing_same_as_shipping=True,
        supplier_name=supplier.name,
        supplier_company_id=supplier.company_id,
        supplier_vat_id=supplier.vat_id,
        supplier_email=supplier.email,
        supplier_phone=supplier.phone,
        supplier_street_line_1=supplier.street_line_1,
        supplier_street_line_2=supplier.street_line_2,
        supplier_city=supplier.city,
        supplier_postal_code=supplier.postal_code,
        supplier_country=supplier.country,
        supplier_bank_name=supplier.bank_name,
        supplier_account_number=supplier.account_number,
        supplier_iban=supplier.iban,
        supplier_swift=supplier.swift,
    )
    order.save()
    return order


def _create_order_items(*, order: Order, cart_pricing) -> None:
    for line in cart_pricing.items:
        item = line.item
        unit_pricing = line.unit_pricing

        if unit_pricing is not None:
            unit_gross = unit_pricing.discounted.gross.amount
            line_total = (unit_gross * Decimal(str(line.quantity))).quantize(
                MONEY_QUANTIZE,
                rounding=ROUND_HALF_UP,
            )
            discount_type = unit_pricing.discount.promotion_type or None
            if discount_type == "PERCENT":
                discount_value = unit_pricing.discount.percentage
            elif discount_type == "FIXED":
                discount_value = unit_pricing.discount.amount_gross.amount
            else:
                discount_type = None
                discount_value = None

            snap_unit_price_net = unit_pricing.discounted.net.amount
            snap_unit_price_gross = unit_gross
            snap_tax_amount = unit_pricing.discounted.tax.amount
            snap_tax_rate = unit_pricing.discounted.tax_rate
            snap_promo_code = unit_pricing.discount.promotion_code
            snap_promo_type = unit_pricing.discount.promotion_type
            snap_promo_discount_gross = (
                unit_pricing.discount.amount_gross.amount
                if unit_pricing.discount.promotion_type
                else None
            )
            snap_line_total_net = (
                snap_unit_price_net * Decimal(str(line.quantity))
            ).quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)
            snap_line_total_gross = line_total
        else:
            unit_gross = item.price_at_add_time
            line_total = (
                item.price_at_add_time * Decimal(str(line.quantity))
            ).quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)
            discount_type = None
            discount_value = None
            snap_unit_price_net = None
            snap_unit_price_gross = None
            snap_tax_amount = None
            snap_tax_rate = None
            snap_promo_code = None
            snap_promo_type = None
            snap_promo_discount_gross = None
            snap_line_total_net = None
            snap_line_total_gross = line_total

        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price_at_order_time=line_total,
            unit_price_at_order_time=unit_gross,
            line_total_at_order_time=line_total,
            applied_discount_type_at_order_time=discount_type,
            applied_discount_value_at_order_time=discount_value,
            unit_price_net_at_order_time=snap_unit_price_net,
            unit_price_gross_at_order_time=snap_unit_price_gross,
            tax_amount_at_order_time=snap_tax_amount,
            tax_rate_at_order_time=snap_tax_rate,
            promotion_code_at_order_time=snap_promo_code,
            promotion_type_at_order_time=snap_promo_type,
            promotion_discount_gross_at_order_time=snap_promo_discount_gross,
            product_name_at_order_time=item.product.name,
            line_total_net_at_order_time=snap_line_total_net,
            line_total_gross_at_order_time=snap_line_total_gross,
        )


def _persist_order_totals(*, order: Order, cart_pricing) -> None:
    order_discount = cart_pricing.order_discount
    if order_discount is not None:
        subtotal_gross = order_discount.total_gross_after.amount
        total_tax = order_discount.total_tax_after.amount
        order_discount_gross = order_discount.gross_reduction.amount
        order_promotion_code = order_discount.promotion_code
    else:
        subtotal_gross = cart_pricing.subtotal_discounted.amount
        total_tax = cart_pricing.total_tax.amount
        order_discount_gross = None
        order_promotion_code = None

    order.subtotal_gross = subtotal_gross
    order.subtotal_net = (subtotal_gross - total_tax).quantize(
        MONEY_QUANTIZE,
        rounding=ROUND_HALF_UP,
    )
    order.total_tax = total_tax
    order.total_discount = (
        cart_pricing.total_discount.amount + (order_discount_gross or Decimal("0.00"))
    ).quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)
    order.order_discount_gross = order_discount_gross
    order.order_promotion_code = order_promotion_code
    order.currency = cart_pricing.currency
    order.save(
        update_fields=[
            "subtotal_net",
            "subtotal_gross",
            "total_tax",
            "total_discount",
            "order_discount_gross",
            "order_promotion_code",
            "currency",
        ]
    )


def _complete_card_payment(*, order: Order, order_data: dict[str, Any]) -> Payment:
    payment = Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        payment_method=Payment.PaymentMethod.CARD,
        provider=Payment.Provider.ACQUIREMOCK,
        provider_payment_id=order_data["provider_payment_id"],
        amount=order.subtotal_gross,
        currency=order.currency,
        redirect_url=order_data["payment_redirect_url"],
    )

    paid_event = AcquireMockWebhookEvent(
        payment_id=order_data["provider_payment_id"],
        reference=order_data["reference"],
        amount=str(order.subtotal_gross),
        status="PAID",
        timestamp="2026-04-21T12:00:00Z",
        raw={
            "payment_id": order_data["provider_payment_id"],
            "reference": order_data["reference"],
            "amount": str(order.subtotal_gross),
            "status": "PAID",
            "timestamp": "2026-04-21T12:00:00Z",
        },
    )
    process_acquiremock_webhook_event(paid_event)
    payment.refresh_from_db()
    return payment


def _apply_shipment_history(*, order: Order, webhook_statuses: list[str]) -> None:
    shipment = Shipment.objects.get(order=order)
    for status in webhook_statuses:
        if status == "PAID":
            continue
        ShipmentEventService.simulate_admin_event(
            shipment=shipment,
            normalized_status=getattr(ShipmentStatus, status),
        )
        shipment.refresh_from_db()
        order.refresh_from_db()


def _cancel_seeded_order(*, order: Order, order_data: dict[str, Any]) -> None:
    cancel_data = order_data["cancel"]
    release_reservations(
        order=order,
        reason=getattr(InventoryReservation.ReleaseReason, cancel_data["release_reason"]),
        cancelled_by=getattr(Order.CancelledBy, cancel_data["cancelled_by"]),
        cancel_reason=getattr(Order.CancelReason, cancel_data["cancel_reason"]),
    )