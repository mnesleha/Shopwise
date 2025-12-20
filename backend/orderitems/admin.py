from django.contrib import admin
from .models import OrderItem
from orders.models import Order


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderWithItemsAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
