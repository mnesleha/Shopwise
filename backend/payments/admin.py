from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "status", "payment_method", "provider", "amount", "currency", "paid_at", "failed_at", "created_at")
    list_filter = ("status", "provider", "payment_method")
    readonly_fields = ("paid_at", "failed_at", "created_at")
