from django.core.files.base import ContentFile

from shipping.models import Shipment
from shipping.providers.base import CreateShipmentContext
from shipping.providers.resolver import resolve_provider
from shipping.services.eligibility import ShipmentEligibilityService


class InvalidShipmentSnapshot(ValueError):
    pass


class ShipmentService:
    @staticmethod
    def create_for_order(*, order):
        if not ShipmentEligibilityService.can_create_shipment(order=order):
            raise ValueError("Shipment can only be created for fulfillment-eligible orders.")

        missing_fields = []
        if not order.shipping_provider_code:
            missing_fields.append("shipping_provider_code")
        if not order.shipping_service_code:
            missing_fields.append("shipping_service_code")
        if missing_fields:
            missing_fields_display = ", ".join(missing_fields)
            raise InvalidShipmentSnapshot(
                f"Shipment cannot be created for order without a complete shipping snapshot: {missing_fields_display}."
            )

        existing_shipment = Shipment.objects.filter(order=order).first()
        if existing_shipment is not None:
            return existing_shipment

        return ShipmentService._create_shipment(
            order=order,
            provider_code=order.shipping_provider_code,
            service_code=order.shipping_service_code,
        )

    @staticmethod
    def create_for_paid_order(*, order):
        return ShipmentService.create_for_order(order=order)

    @staticmethod
    def create_retry_for_order(*, order, provider_code: str | None = None, service_code: str | None = None):
        return ShipmentService._create_shipment(
            order=order,
            provider_code=provider_code or order.shipping_provider_code,
            service_code=service_code or order.shipping_service_code,
        )

    @staticmethod
    def _create_shipment(*, order, provider_code: str | None, service_code: str | None):
        missing_fields = []
        if not provider_code:
            missing_fields.append("shipping_provider_code")
        if not service_code:
            missing_fields.append("shipping_service_code")
        if missing_fields:
            missing_fields_display = ", ".join(missing_fields)
            raise InvalidShipmentSnapshot(
                f"Shipment cannot be created for order without a complete shipping snapshot: {missing_fields_display}."
            )

        provider = resolve_provider(provider_code)
        context = ShipmentService._build_create_context(
            order=order,
            service_code=service_code,
        )
        provider_result = provider.create_shipment(
            context
        )

        shipment = Shipment(
            order=order,
            provider_code=provider_result.provider_code,
            service_code=provider_result.service_code,
            carrier_name_snapshot=provider_result.carrier_name,
            service_name_snapshot=provider_result.service_name,
            tracking_number=provider_result.tracking_number,
            carrier_reference=provider_result.carrier_reference,
            status=provider_result.status,
            label_url=provider_result.label_url,
            receiver_snapshot=provider_result.receiver_snapshot,
            meta=provider_result.meta,
        )

        label_document = provider.build_label_document(
            context=context,
            provider_result=provider_result,
        )
        if label_document is not None:
            shipment.label_file.save(
                label_document.filename,
                ContentFile(label_document.content),
                save=False,
            )
            shipment.label_url = shipment.get_label_url()

        shipment.save()
        ShipmentService._sync_order_projection(order=order, shipment=shipment)
        return shipment

    @staticmethod
    def _build_create_context(*, order, service_code: str) -> CreateShipmentContext:
        shipment_attempt = Shipment.objects.filter(order=order).count() + 1
        return CreateShipmentContext(
            order=order,
            service_code=service_code,
            receiver={
                "first_name": order.shipping_first_name,
                "last_name": order.shipping_last_name,
                "address_line1": order.shipping_address_line1,
                "address_line2": order.shipping_address_line2 or "",
                "city": order.shipping_city,
                "postal_code": order.shipping_postal_code,
                "country": order.shipping_country,
                "phone": order.shipping_phone,
                "company": order.shipping_company or "",
                "company_id": order.shipping_company_id or "",
                "vat_id": order.shipping_vat_id or "",
            },
            extra={
                "shipment_attempt": shipment_attempt,
            },
        )

    @staticmethod
    def _sync_order_projection(*, order, shipment) -> None:
        from shipping.services.events import ShipmentEventService

        ShipmentEventService.sync_order_projection(order=order, shipment=shipment)