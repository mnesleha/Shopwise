from django import forms
from django.contrib import admin
from martor.widgets import AdminMartorWidget
from .models import Product, ProductImage


# ---------------------------------------------------------------------------
# ProductImage inline
# ---------------------------------------------------------------------------


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    # ``ppoi`` is NOT listed here: it is handled automatically by the image
    # multi-widget (SizedImageCenterpointClickDjangoAdminWidget) when
    # ppoi_field is set on the model field.  Listing it as a separate field
    # would show a redundant text input alongside the click widget.
    # To edit PPOI for an existing image, follow the change link to the
    # ProductImage detail page where the click widget renders correctly.
    fields = ("image", "alt_text", "sort_order")
    show_change_link = True


# ---------------------------------------------------------------------------
# Product admin
# ---------------------------------------------------------------------------


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
        "primary_image",
    )
    inlines = [ProductImageInline]

    def get_form(self, request, obj=None, **kwargs):
        """Restrict primary_image choices to images belonging to the current product."""
        form = super().get_form(request, obj, **kwargs)
        if "primary_image" in form.base_fields:
            if obj is not None:
                form.base_fields["primary_image"].queryset = (
                    ProductImage.objects.filter(product=obj)
                )
            else:
                # New product — no images exist yet; keep queryset empty.
                form.base_fields["primary_image"].queryset = (
                    ProductImage.objects.none()
                )
        return form

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Use the Martor rich-text widget only for full_description."""
        if db_field.name == "full_description":
            kwargs["widget"] = AdminMartorWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """Standalone admin for ProductImage.

    This is the canonical place to edit PPOI (focal point).  When
    ``ppoi_field`` is set on the ``VersatileImageField`` the ``image``
    form field renders ``SizedImageCenterpointClickDjangoAdminField``,
    which shows a clickable preview thumbnail — click to reposition the
    focal point, then save.
    """

    list_display = ("id", "product", "alt_text", "sort_order", "created_at")
    list_filter = ("product",)
    # ``ppoi`` is intentionally omitted: it is populated automatically by
    # the ``image`` field's multi-widget and saved via pre_save().
    fields = ("product", "image", "alt_text", "sort_order")

