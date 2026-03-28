from django.contrib import admin

from shipping.models import Shipment, ShipmentEvent


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
    )
    raw_id_fields = ("order",)
    list_select_related = ("order",)
    inlines = (ShipmentEventInline,)


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