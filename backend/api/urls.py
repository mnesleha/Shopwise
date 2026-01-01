from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.products import ProductViewSet, ProductListView
from api.views.categories import CategoryViewSet
from api.views.carts import CartCheckoutView
from api.views.orders import OrderViewSet
from api.views.discounts import DiscountViewSet
from api.views.carts import CartView, CartItemCreateView
from api.views.payments import PaymentCreateView
from api.views.auth import LoginView, CsrfTokenView
from api.views import health_check

app_name = "api"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register(r"orders", OrderViewSet, basename="order")
router.register("discounts", DiscountViewSet, basename="discount")


urlpatterns = [
    path("health/", health_check, name="health"),
    path("", include(router.urls)),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemCreateView.as_view(), name="cart-item-create"),
    path("cart/checkout/", CartCheckoutView.as_view()),
    path("payments/", PaymentCreateView.as_view(), name="payment-create"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/csrf/", CsrfTokenView.as_view(), name="csrf"),
]
