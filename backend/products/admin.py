from django.contrib import admin
from martor.widgets import AdminMartorWidget
from django.db import models
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "stock_quantity", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    fields = (
        "name",
        "price",
        "stock_quantity",
        "is_active",
        "category",
        "short_description",
        "full_description",
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Use the Martor rich-text widget only for full_description."""
        if db_field.name == "full_description":
            kwargs["widget"] = AdminMartorWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)
