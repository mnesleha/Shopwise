from django.contrib import admin, messages
from django.utils.html import format_html

from shipping.models import Shipment, ShipmentEvent
from shipping.services.events import InvalidShipmentSimulation, ShipmentEventService
from shipping.statuses import ShipmentStatus


class ShipmentEventInline(admin.TabularInline):
    model = ShipmentEvent
    extra = 0
    can_delete = False
    fields = (
        "event_type",
        "raw_status",
        "normalized_status",
        "external_event_id",
        "occurred_at",
        "processed_at",
        "payload",
        "created_at",
    )
    readonly_fields = fields
    show_change_link = True


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    actions = ("simulate_in_transit", "simulate_delivered")
    list_display = (
        "id",
        "order",
        "provider_code",
        "service_code",
        "status",
        "tracking_number",
        "carrier_reference",
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
        "created_at",
        "updated_at",
        "receiver_snapshot",
        "meta",
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

    @admin.action(description="Simulate shipment in transit")
    def simulate_in_transit(self, request, queryset):
        self._simulate_status(request, queryset, ShipmentStatus.IN_TRANSIT)

    @admin.action(description="Simulate shipment delivered")
    def simulate_delivered(self, request, queryset):
        self._simulate_status(request, queryset, ShipmentStatus.DELIVERED)

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
        "shipment",
        "event_type",
        "raw_status",
        "normalized_status",
        "external_event_id",
        "occurred_at",
        "processed_at",
        "created_at",
    )
    list_filter = ("normalized_status", "event_type")
    search_fields = (
        "id",
        "shipment__id",
        "external_event_id",
        "shipment__tracking_number",
    )
    readonly_fields = (
        "payload",
        "occurred_at",
        "processed_at",
        "created_at",
    )
    raw_id_fields = ("shipment",)
    list_select_related = ("shipment",)