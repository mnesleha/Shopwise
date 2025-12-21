from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.products import ProductViewSet
from api.views.categories import CategoryViewSet
from api.views import health_check

app_name = "api"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("health/", health_check, name="health"),
    path("", include(router.urls)),
]
