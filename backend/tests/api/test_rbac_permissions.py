import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIRequestFactory

from orders.models import Order

# New modules introduced by RBAC PR:
from api.permissions import IsStaffOrHasDjangoPerm
from accounts.permissions import ORDERS_CAN_FULFILL


class DummyView:
    # DRF permissions receive (request, view)
    pass


@pytest.mark.django_db
def test_permission_denies_unauthenticated():
    factory = APIRequestFactory()
    request = factory.get("/api/v1/admin/something/")

    perm = IsStaffOrHasDjangoPerm(ORDERS_CAN_FULFILL)
    assert perm.has_permission(request, DummyView()) is False


@pytest.mark.django_db
def test_permission_allows_superuser():
    User = get_user_model()
    su = User.objects.create_superuser(
        email="su@example.com", password="Passw0rd!123")

    factory = APIRequestFactory()
    request = factory.get("/api/v1/admin/something/")
    request.user = su

    perm = IsStaffOrHasDjangoPerm(ORDERS_CAN_FULFILL)
    assert perm.has_permission(request, DummyView()) is True


@pytest.mark.django_db
def test_permission_allows_staff_fallback_mvp():
    User = get_user_model()
    staff = User.objects.create_user(
        email="staff@example.com",
        password="Passw0rd!123",
        is_staff=True,
    )

    factory = APIRequestFactory()
    request = factory.get("/api/v1/admin/something/")
    request.user = staff

    perm = IsStaffOrHasDjangoPerm(ORDERS_CAN_FULFILL)
    assert perm.has_permission(request, DummyView()) is True


@pytest.mark.django_db
def test_permission_allows_user_with_explicit_django_permission():
    User = get_user_model()
    u = User.objects.create_user(
        email="ops@example.com", password="Passw0rd!123")

    # Grant the fulfill permission explicitly
    ct = ContentType.objects.get_for_model(Order)
    p = Permission.objects.get(content_type=ct, codename="can_fulfill")
    u.user_permissions.add(p)

    factory = APIRequestFactory()
    request = factory.get("/api/v1/admin/something/")
    request.user = u

    perm = IsStaffOrHasDjangoPerm(ORDERS_CAN_FULFILL)
    assert perm.has_permission(request, DummyView()) is True


@pytest.mark.django_db
def test_permission_denies_user_without_staff_or_permission():
    User = get_user_model()
    u = User.objects.create_user(
        email="nope@example.com", password="Passw0rd!123")

    factory = APIRequestFactory()
    request = factory.get("/api/v1/admin/something/")
    request.user = u

    perm = IsStaffOrHasDjangoPerm(ORDERS_CAN_FULFILL)
    assert perm.has_permission(request, DummyView()) is False
