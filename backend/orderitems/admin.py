from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import OrderItem
from orders.models import Order


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


def _filter_orders_by_current_shipment(queryset, predicate):
    matching_ids = [order.pk for order in queryset if predicate(order)]
    return queryset.filter(pk__in=matching_ids)


class CurrentShipmentStatusFilter(admin.SimpleListFilter):
    title = "Current shipment status"
    parameter_name = "current_shipment_status"

    def lookups(self, request, model_admin):
        return (
            ("no_shipment", "No shipment"),
            ("LABEL_CREATED", "Label created"),
            ("IN_TRANSIT", "In transit"),
            ("DELIVERED", "Delivered"),
            ("FAILED_DELIVERY", "Failed delivery"),
            ("CANCELLED", "Cancelled"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        if value == "no_shipment":
            return _filter_orders_by_current_shipment(
                queryset,
                lambda order: order.get_current_shipment() is None,
            )

        return _filter_orders_by_current_shipment(
            queryset,
            lambda order: (
                order.get_current_shipment() is not None
                and order.get_current_shipment().status == value
            ),
        )


class ShippingProviderFilter(admin.SimpleListFilter):
    title = "Shipping provider"
    parameter_name = "shipping_provider"

    def lookups(self, request, model_admin):
        queryset = model_admin.get_queryset(request)
        providers = sorted(
            {
                shipment.provider_code
                for order in queryset
                for shipment in [order.get_current_shipment()]
                if shipment is not None and shipment.provider_code
            }
        )
        return [(provider, provider) for provider in providers]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        return _filter_orders_by_current_shipment(
            queryset,
            lambda order: (
                order.get_current_shipment() is not None
                and order.get_current_shipment().provider_code == value
            ),
        )


class ShippingMethodFilter(admin.SimpleListFilter):
    title = "Shipping method"
    parameter_name = "shipping_method"

    def lookups(self, request, model_admin):
        queryset = model_admin.get_queryset(request)
        methods = sorted(
            {
                shipment.service_name_snapshot or shipment.service_code
                for order in queryset
                for shipment in [order.get_current_shipment()]
                if shipment is not None and (shipment.service_name_snapshot or shipment.service_code)
            }
        )
        return [(method, method) for method in methods]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        return _filter_orders_by_current_shipment(
            queryset,
            lambda order: (
                order.get_current_shipment() is not None
                and (order.get_current_shipment().service_name_snapshot or order.get_current_shipment().service_code) == value
            ),
        )


class HasShipmentFilter(admin.SimpleListFilter):
    title = "Has shipment"
    parameter_name = "has_shipment"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(shipments__isnull=False).distinct()
        if value == "no":
            return queryset.filter(shipments__isnull=True)
        return queryset


class HasLabelFilter(admin.SimpleListFilter):
    title = "Has label"
    parameter_name = "has_label"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        return _filter_orders_by_current_shipment(
            queryset,
            lambda order: (
                (order.get_current_shipment() is not None and bool(order.get_current_shipment().get_label_url()))
                if value == "yes"
                else (order.get_current_shipment() is None or not order.get_current_shipment().get_label_url())
            ),
        )


class HasTrackingNumberFilter(admin.SimpleListFilter):
    title = "Has tracking number"
    parameter_name = "has_tracking"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        return _filter_orders_by_current_shipment(
            queryset,
            lambda order: (
                (order.get_current_shipment() is not None and bool(order.get_current_shipment().tracking_number))
                if value == "yes"
                else (order.get_current_shipment() is None or not order.get_current_shipment().tracking_number)
            ),
        )


class ShippingExceptionFilter(admin.SimpleListFilter):
    title = "Shipping exceptions"
    parameter_name = "shipping_exception"

    def lookups(self, request, model_admin):
        return (
            ("paid_without_shipment", "Paid but missing shipment"),
            ("shipment_without_label", "Shipment without label"),
            ("shipment_without_tracking", "Shipment without tracking"),
            ("multiple_shipments", "Multiple shipments"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        if value == "paid_without_shipment":
            return queryset.filter(status=Order.Status.PAID, shipments__isnull=True)

        if value == "multiple_shipments":
            return _filter_orders_by_current_shipment(
                queryset,
                lambda order: order.get_shipment_count() > 1,
            )

        if value == "shipment_without_label":
            return _filter_orders_by_current_shipment(
                queryset,
                lambda order: (
                    order.get_current_shipment() is not None
                    and not order.get_current_shipment().get_label_url()
                ),
            )

        if value == "shipment_without_tracking":
            return _filter_orders_by_current_shipment(
                queryset,
                lambda order: (
                    order.get_current_shipment() is not None
                    and not order.get_current_shipment().tracking_number
                ),
            )

        return queryset


@admin.register(Order)
class OrderWithItemsAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = (
        "id",
        "status",
        "customer_email",
        "current_shipment_status",
        "current_shipping_method",
        "current_shipping_provider",
        "current_tracking_number",
        "shipment_count",
        "shipping_links",
        "created_at",
    )
    list_filter = (
        "status",
        CurrentShipmentStatusFilter,
        ShippingProviderFilter,
        ShippingMethodFilter,
        HasShipmentFilter,
        HasLabelFilter,
        HasTrackingNumberFilter,
        ShippingExceptionFilter,
    )
    search_fields = (
        "id",
        "customer_email",
        "customer_email_normalized",
        "shipments__tracking_number",
    )
    readonly_fields = (
        "created_at",
        "current_shipment_status",
        "current_shipping_method",
        "current_shipping_provider",
        "current_tracking_number",
        "shipment_count",
        "current_shipment_detail_link",
        "current_label_link",
        "current_public_tracking_link",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user").prefetch_related("shipments")

    def get_fieldsets(self, request, obj=None):
        editable_model_fields = [
            field.name
            for field in self.model._meta.fields
            if field.editable and not field.auto_created and not field.primary_key
        ]
        return (
            (None, {"fields": (*editable_model_fields, "created_at")}),
            (
                "Current shipment summary",
                {
                    "fields": (
                        "current_shipment_status",
                        "current_shipping_method",
                        "current_shipping_provider",
                        "current_tracking_number",
                        "shipment_count",
                        "current_shipment_detail_link",
                        "current_label_link",
                        "current_public_tracking_link",
                    )
                },
            ),
        )

    @admin.display(description="Shipment status")
    def current_shipment_status(self, obj):
        shipment = obj.get_current_shipment()
        if shipment is None:
            return "No shipment"
        return shipment.get_status_display()

    @admin.display(description="Shipping method")
    def current_shipping_method(self, obj):
        shipment = obj.get_current_shipment()
        if shipment is None:
            return "-"
        return shipment.service_name_snapshot or shipment.service_code or "-"

    @admin.display(description="Shipping provider")
    def current_shipping_provider(self, obj):
        shipment = obj.get_current_shipment()
        if shipment is None:
            return "-"
        return shipment.provider_code or "-"

    @admin.display(description="Tracking number")
    def current_tracking_number(self, obj):
        shipment = obj.get_current_shipment()
        if shipment is None or not shipment.tracking_number:
            return "-"
        return shipment.tracking_number

    @admin.display(description="Shipment count")
    def shipment_count(self, obj):
        return obj.get_shipment_count()

    @admin.display(description="Shipping")
    def shipping_links(self, obj):
        shipment = obj.get_current_shipment()
        if shipment is None:
            return "-"

        shipment_link = format_html(
            '<a href="{}">Open shipment</a>',
            reverse("admin:shipping_shipment_change", args=[shipment.pk]),
        )
        if not shipment.get_label_url():
            return shipment_link

        label_link = format_html(
            '<a href="{}" target="_blank" rel="noreferrer">Open label</a>',
            shipment.get_label_url(),
        )
        return format_html("{} | {}", shipment_link, label_link)

    @admin.display(description="Open shipment")
    def current_shipment_detail_link(self, obj):
        shipment = obj.get_current_shipment()
        if shipment is None:
            return "-"
        return format_html(
            '<a href="{}">Open shipment detail</a>',
            reverse("admin:shipping_shipment_change", args=[shipment.pk]),
        )

    @admin.display(description="Open label")
    def current_label_link(self, obj):
        shipment = obj.get_current_shipment()
        if shipment is None or not shipment.get_label_url():
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noreferrer">Open label</a>',
            shipment.get_label_url(),
        )

    @admin.display(description="Public tracking")
    def current_public_tracking_link(self, obj):
        shipment = obj.get_current_shipment()
        if shipment is None or not shipment.tracking_number:
            return "-"
        return format_html(
            '<a href="/tracking/{}" target="_blank" rel="noreferrer">Open tracking</a>',
            shipment.tracking_number,
        )
