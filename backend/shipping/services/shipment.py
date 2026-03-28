from shipping.models import Shipment
from shipping.providers.base import CreateShipmentContext
from shipping.providers.resolver import resolve_provider


class InvalidShipmentSnapshot(ValueError):
    pass


class ShipmentService:
    @staticmethod
    def create_for_paid_order(*, order):
        if order.status != order.Status.PAID:
            raise ValueError("Shipment can only be created for PAID orders.")

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

        provider = resolve_provider(order.shipping_provider_code)
        provider_result = provider.create_shipment(
            CreateShipmentContext(
                order=order,
                service_code=order.shipping_service_code,
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
            )
        )

        return Shipment.objects.create(
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