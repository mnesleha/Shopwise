from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.products import ProductViewSet
from api.views.categories import CategoryViewSet
from api.views.orders import OrderViewSet
from api.views.discounts import DiscountViewSet
from api.views.carts import CartView, CartItemCreateView
from api.views import health_check

app_name = "api"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("orders", OrderViewSet, basename="order")
router.register("discounts", DiscountViewSet, basename="discount")


urlpatterns = [
    path("health/", health_check, name="health"),
    path("", include(router.urls)),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemCreateView.as_view(), name="cart-item-create"),
]
