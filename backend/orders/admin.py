from django.contrib import admin
from .models import Order, InventoryReservation


@admin.register(InventoryReservation)
class InventoryReservationAdmin(admin.ModelAdmin):
    list_display = ("order_id", "product", "quantity", "status", "expires_at",
                    "committed_at", "released_at", "release_reason", "created_at")
    list_filter = ("status", "release_reason")
    search_fields = ("order__id", "product__name")
