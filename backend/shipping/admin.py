import json

from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from orders.models import Order
from shipping.models import Shipment, ShipmentEvent
from shipping.services.events import InvalidShipmentSimulation, ShipmentEventService
from shipping.services.fulfillment import OrderFulfillmentService
from shipping.statuses import ShipmentStatus


class ShipmentEventInline(admin.TabularInline):
    model = ShipmentEvent
    extra = 0
    can_delete = False
    fields = (
        "event_summary",
        "source_summary",
        "normalized_status_label",
        "occurred_at",
        "external_event_id",
        "processed_at",
        "created_at",
    )
    readonly_fields = fields
    show_change_link = True

    @admin.display(description="Event")
    def event_summary(self, obj):
        return _format_event_label(obj.event_type)

    @admin.display(description="Source")
    def source_summary(self, obj):
        return _format_event_source(obj)

    @admin.display(description="Resulting status")
    def normalized_status_label(self, obj):
        return obj.get_normalized_status_display()


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    actions = (
        "simulate_in_transit",
        "simulate_delivered",
        "simulate_failed_delivery",
        "retry_failed_delivery",
    )
    list_display = (
        "id",
        "order_summary",
        "shipment_status_label",
        "shipping_service_summary",
        "tracking_number",
        "carrier_reference",
        "operations_links",
        "shipped_at",
        "delivered_at",
        "created_at",
    )
    list_filter = ("status", "provider_code", "service_code")
    search_fields = (
        "id",
        "order__id",
        "tracking_number",
        "carrier_reference",
    )
    readonly_fields = (
        "order_summary",
        "shipment_status_label",
        "shipping_service_summary",
        "order_admin_link",
        "public_tracking_link",
        "created_at",
        "updated_at",
        "receiver_snapshot_pretty",
        "meta_pretty",
        "shipped_at",
        "delivered_at",
        "label_asset_link",
    )
    raw_id_fields = ("order",)
    list_select_related = ("order",)
    inlines = (ShipmentEventInline,)

    @admin.display(description="Label")
    def label_asset_link(self, obj):
        label_url = obj.get_label_url()
        if not label_url:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noreferrer">Open label</a>',
            label_url,
        )

    @admin.display(description="Order")
    def order_summary(self, obj):
        return format_html(
            '<a href="{}">Order #{} ({})</a>',
            reverse("admin:orders_order_change", args=[obj.order_id]),
            obj.order_id,
            obj.order.get_status_display(),
        )

    @admin.display(description="Status")
    def shipment_status_label(self, obj):
        return obj.get_status_display()

    @admin.display(description="Provider / service")
    def shipping_service_summary(self, obj):
        service_label = obj.service_name_snapshot or obj.service_code or "-"
        return f"{obj.provider_code} / {service_label}"

    @admin.display(description="Links")
    def operations_links(self, obj):
        links = [
            format_html(
                '<a href="{}">Order</a>',
                reverse("admin:orders_order_change", args=[obj.order_id]),
            )
        ]
        label_url = obj.get_label_url()
        if label_url:
            links.append(
                format_html(
                    '<a href="{}" target="_blank" rel="noreferrer">Label</a>',
                    label_url,
                )
            )
        if obj.tracking_number:
            links.append(
                format_html(
                    '<a href="/tracking/{}" target="_blank" rel="noreferrer">Public tracking</a>',
                    obj.tracking_number,
                )
            )
        return format_html(" | ".join("{}" for _ in links), *links)

    @admin.display(description="Open order")
    def order_admin_link(self, obj):
        return format_html(
            '<a href="{}">Open order</a>',
            reverse("admin:orders_order_change", args=[obj.order_id]),
        )

    @admin.display(description="Public tracking")
    def public_tracking_link(self, obj):
        if not obj.tracking_number:
            return "-"
        return format_html(
            '<a href="/tracking/{}" target="_blank" rel="noreferrer">Open public tracking</a>',
            obj.tracking_number,
        )

    @admin.display(description="Receiver snapshot")
    def receiver_snapshot_pretty(self, obj):
        return _format_json_block(obj.receiver_snapshot)

    @admin.display(description="Technical metadata")
    def meta_pretty(self, obj):
        return _format_json_block(obj.meta)

    def get_fieldsets(self, request, obj=None):
        return (
            (
                "Operations summary",
                {
                    "fields": (
                        "order",
                        "order_summary",
                        "shipment_status_label",
                        "provider_code",
                        "service_code",
                        "shipping_service_summary",
                        "tracking_number",
                        "carrier_reference",
                        "order_admin_link",
                        "label_asset_link",
                        "public_tracking_link",
                    )
                },
            ),
            (
                "Shipment timeline",
                {
                    "fields": (
                        "created_at",
                        "shipped_at",
                        "delivered_at",
                        "updated_at",
                    )
                },
            ),
            (
                "Receiver details",
                {
                    "fields": (
                        "receiver_snapshot_pretty",
                    )
                },
            ),
            (
                "Technical details",
                {
                    "fields": (
                        "meta_pretty",
                    ),
                    "classes": ("collapse",),
                },
            ),
        )

    @admin.action(description="Simulate shipment in transit")
    def simulate_in_transit(self, request, queryset):
        self._simulate_status(request, queryset, ShipmentStatus.IN_TRANSIT)

    @admin.action(description="Simulate shipment delivered")
    def simulate_delivered(self, request, queryset):
        self._simulate_status(request, queryset, ShipmentStatus.DELIVERED)

    @admin.action(description="Simulate shipment failed delivery")
    def simulate_failed_delivery(self, request, queryset):
        self._simulate_status(request, queryset, ShipmentStatus.FAILED_DELIVERY)

    @admin.action(description="Retry failed delivery")
    def retry_failed_delivery(self, request, queryset):
        order_ids: list[int] = []
        seen_order_ids: set[int] = set()
        for shipment in queryset.select_related("order"):
            if shipment.order_id in seen_order_ids:
                continue
            seen_order_ids.add(shipment.order_id)
            order_ids.append(shipment.order_id)

        result = OrderFulfillmentService.bulk_retry_failed_delivery(
            orders=Order.objects.filter(pk__in=order_ids),
        )
        level = messages.SUCCESS if result.updated_count else messages.WARNING
        self.message_user(
            request,
            result.build_message(
                action_name="Retry failed delivery",
                reason_labels={
                    "no_current_shipment": "no current shipment exists",
                    "invalid_shipment_status": "current shipment is not FAILED_DELIVERY",
                    "invalid_shipping_snapshot": "shipping snapshot is incomplete",
                    "provider_not_configured": "shipping provider is not configured",
                },
            ),
            level=level,
        )

    def _simulate_status(self, request, queryset, normalized_status: str) -> None:
        processed_count = 0
        for shipment in queryset:
            try:
                ShipmentEventService.simulate_admin_event(
                    shipment=shipment,
                    normalized_status=normalized_status,
                )
            except InvalidShipmentSimulation as exc:
                self.message_user(request, f"Shipment #{shipment.pk}: {exc}", level=messages.ERROR)
                continue

            processed_count += 1

        if processed_count:
            self.message_user(
                request,
                f"Simulated {normalized_status.lower()} for {processed_count} shipment(s).",
                level=messages.SUCCESS,
            )


@admin.register(ShipmentEvent)
class ShipmentEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "shipment_admin_link",
        "order_admin_link",
        "event_summary",
        "source_summary",
        "normalized_status_label",
        "external_event_id",
        "occurred_at",
        "processed_at",
    )
    list_filter = ("normalized_status", "event_type")
    search_fields = (
        "id",
        "shipment__id",
        "shipment__order__id",
        "external_event_id",
        "shipment__tracking_number",
    )
    readonly_fields = (
        "shipment_admin_link",
        "order_admin_link",
        "event_summary",
        "source_summary",
        "normalized_status_label",
        "payload_pretty",
        "raw_status",
        "external_event_id",
        "event_type",
        "normalized_status",
        "occurred_at",
        "processed_at",
        "created_at",
    )
    raw_id_fields = ("shipment",)
    list_select_related = ("shipment", "shipment__order")

    @admin.display(description="Shipment")
    def shipment_admin_link(self, obj):
        return format_html(
            '<a href="{}">Shipment #{}</a>',
            reverse("admin:shipping_shipment_change", args=[obj.shipment_id]),
            obj.shipment_id,
        )

    @admin.display(description="Order")
    def order_admin_link(self, obj):
        return format_html(
            '<a href="{}">Order #{} ({})</a>',
            reverse("admin:orders_order_change", args=[obj.shipment.order_id]),
            obj.shipment.order_id,
            obj.shipment.order.get_status_display(),
        )

    @admin.display(description="Event")
    def event_summary(self, obj):
        return _format_event_label(obj.event_type)

    @admin.display(description="Source")
    def source_summary(self, obj):
        return _format_event_source(obj)

    @admin.display(description="Resulting status")
    def normalized_status_label(self, obj):
        return obj.get_normalized_status_display()

    @admin.display(description="Payload")
    def payload_pretty(self, obj):
        return _format_json_block(obj.payload)

    def get_fieldsets(self, request, obj=None):
        return (
            (
                "Event summary",
                {
                    "fields": (
                        "shipment_admin_link",
                        "order_admin_link",
                        "event_summary",
                        "source_summary",
                        "normalized_status_label",
                        "external_event_id",
                        "occurred_at",
                        "processed_at",
                        "created_at",
                    )
                },
            ),
            (
                "Technical details",
                {
                    "fields": (
                        "event_type",
                        "raw_status",
                        "normalized_status",
                        "payload_pretty",
                    ),
                    "classes": ("collapse",),
                },
            ),
        )


def _format_event_label(event_type: str) -> str:
    return str(event_type or "Status update").replace("_", " ").replace("-", " ").title()


def _format_event_source(obj: ShipmentEvent) -> str:
    payload_source = (obj.payload or {}).get("source")
    if payload_source:
        return str(payload_source).replace("_", " ").replace("-", " ").title()
    if obj.external_event_id:
        return "External event"
    return "System"


def _format_json_block(value) -> str:
    content = json.dumps(value or {}, indent=2, sort_keys=True, ensure_ascii=True)
    return format_html("<pre>{}</pre>", content)