from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.products import ProductViewSet
from api.views.categories import CategoryViewSet
from api.views.carts import CartCheckoutView
from api.views.orders import OrderViewSet
from api.views.discounts import DiscountViewSet
from api.views.carts import CartView, CartItemCreateView
from api.views.payments import PaymentCreateView
from api.views.auth import LoginView, RegisterView, MeView, RefreshView, VerifyEmailView
from api.views.dev import DevEmailVerificationTokenView
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
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view()),
    path("auth/verify-email/", VerifyEmailView.as_view()),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path(
        "dev/email-verification-token/",
        DevEmailVerificationTokenView.as_view(),
    ),
]
