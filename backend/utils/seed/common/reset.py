from __future__ import annotations

from collections.abc import Callable

from django.apps import apps


WriteLine = Callable[[str], None]


def safe_delete_all(app_label: str, model_name: str) -> int:
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return 0

    deleted, _ = model.objects.all().delete()
    return deleted


def reset_demo_seed_data(write_line: WriteLine | None = None) -> None:
    write = write_line or (lambda message: None)

    write("Resetting demo seed data...")

    safe_delete_all("payments", "Payment")
    safe_delete_all("orderitems", "OrderItem")
    safe_delete_all("orders", "Order")
    safe_delete_all("carts", "CartItem")
    safe_delete_all("carts", "ActiveCart")
    safe_delete_all("carts", "Cart")

    safe_delete_all("discounts", "Discount")
    safe_delete_all("discounts", "Offer")
    safe_delete_all("discounts", "OrderPromotion")
    safe_delete_all("discounts", "PromotionCategory")
    safe_delete_all("discounts", "PromotionProduct")
    safe_delete_all("discounts", "Promotion")
    safe_delete_all("products", "Product")
    safe_delete_all("categories", "Category")
    safe_delete_all("suppliers", "SupplierPaymentDetails")
    safe_delete_all("suppliers", "SupplierAddress")
    safe_delete_all("suppliers", "Supplier")
    safe_delete_all("products", "TaxClass")

    write("Demo reset done.")