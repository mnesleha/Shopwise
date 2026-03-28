from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.products import ProductViewSet
from api.views.categories import CategoryViewSet
from api.views.carts import CartCheckoutView, CartCheckoutPreflightView, ClaimOfferView
from api.views.orders import OrderViewSet
from api.views.discounts import DiscountViewSet
from api.views.carts import CartView, CartItemCreateView, CartItemDetailView
from api.views.payments import PaymentCreateView
from api.views.webhooks import AcquireMockWebhookView
from api.views.auth import (
    LoginView,
    LogoutView,
    RegisterView,
    MeView,
    RefreshView,
    VerifyEmailView,
    RequestEmailVerificationView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    CartMergeView,
    OrdersClaimView,
)
from api.views.dev import DevEmailVerificationTokenView
from api.views.admin_inventory_reservations import InventoryReservationAdminViewSet
from api.views.admin_orders import AdminOrderViewSet
from api.views.guest_orders import GuestOrderRetrieveView, GuestOrderBootstrapView
from api.views.tracking import PublicTrackingRetrieveView
from api.views import health_check
from api.views.profile import ProfileView, AddressViewSet
from api.views.accounts import AccountView, ChangeEmailView, ConfirmEmailChangeView, CancelEmailChangeView, LogoutAllView, ChangePasswordView
from api.views.descriptions import MartorImageUploadView

app_name = "api"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register(r"orders", OrderViewSet, basename="order")
router.register("discounts", DiscountViewSet, basename="discount")
router.register(
    r"admin/inventory-reservations",
    InventoryReservationAdminViewSet,
    basename="admin-inventory-reservations",
)
router.register(
    r"admin/orders",
    AdminOrderViewSet,
    basename="admin-orders",
)
router.register(r"addresses", AddressViewSet, basename="address")


urlpatterns = [
    path("health/", health_check, name="health"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("account/", AccountView.as_view(), name="account"),
    path("account/change-email/", ChangeEmailView.as_view(), name="account-change-email"),
    path("account/confirm-email-change/", ConfirmEmailChangeView.as_view(), name="account-confirm-email-change"),
    path("account/cancel-email-change/", CancelEmailChangeView.as_view(), name="account-cancel-email-change"),
    path("account/logout-all/", LogoutAllView.as_view(), name="account-logout-all"),
    path("account/change-password/", ChangePasswordView.as_view(), name="account-change-password"),
    # Place before router.urls so this explicit path is not shadowed by
    # the router's orders/<pk>/ pattern.
    path("orders/claim/", OrdersClaimView.as_view(), name="orders-claim"),
    path("", include(router.urls)),
    path(
        "guest/orders/<int:order_id>/",
        GuestOrderRetrieveView.as_view(),
        name="guest-order-detail",
    ),
    path(
        "guest/orders/<int:order_id>/bootstrap/",
        GuestOrderBootstrapView.as_view(),
        name="guest-order-bootstrap",
    ),
    path(
        "tracking/<str:tracking_number>/",
        PublicTrackingRetrieveView.as_view(),
        name="public-tracking-detail",
    ),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemCreateView.as_view(), name="cart-item-create"),
    path(
        "cart/items/<int:product_id>/",
        CartItemDetailView.as_view(),
        name="cart-item-detail",
    ),
    path("cart/offer/claim/", ClaimOfferView.as_view(), name="cart-offer-claim"),
    path("cart/checkout/preflight/", CartCheckoutPreflightView.as_view(), name="cart-checkout-preflight"),
    path("cart/checkout/", CartCheckoutView.as_view()),
    path("cart/merge/", CartMergeView.as_view(), name="cart-merge"),
    path("payments/", PaymentCreateView.as_view(), name="payment-create"),
    path("webhooks/acquiremock/", AcquireMockWebhookView.as_view(), name="webhook-acquiremock"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path(
        "auth/request-email-verification/",
        RequestEmailVerificationView.as_view(),
    ),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/password-reset/request/", PasswordResetRequestView.as_view(), name="auth-password-reset-request"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path(
        "dev/email-verification-token/",
        DevEmailVerificationTokenView.as_view(),
    ),
    path('descriptions/upload/', MartorImageUploadView.as_view(), name='description-image-upload'),
]
