import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from orders.models import Order

# New modules introduced by RBAC PR:
from accounts.roles import Role
from accounts import permissions as perm_consts
from accounts.rbac import sync_rbac, ROLE_GROUP
from api.exceptions.accounts import MissingRBACPermissionsError


@pytest.mark.django_db
def test_sync_rbac_creates_groups_and_assigns_permissions():
    # Ensure clean slate for groups we manage
    Group.objects.filter(name__in=set(ROLE_GROUP.values())).delete()

    # Run RBAC sync
    call_command("sync_rbac")

    # Groups exist
    for role, group_name in ROLE_GROUP.items():
        assert Group.objects.filter(name=group_name).exists(
        ), f"Missing group for role {role}: {group_name}"

    # Permissions exist in DB (created via Django permission framework from Order.Meta.permissions)
    ct = ContentType.objects.get_for_model(Order)
    # Required perms (MVP)
    p_fulfill = Permission.objects.get(content_type=ct, codename="can_fulfill")
    p_cancel_admin = Permission.objects.get(
        content_type=ct, codename="can_cancel_admin")

    # Group permission assignment
    ops = Group.objects.get(name=ROLE_GROUP[Role.WAREHOUSE_MANAGER])
    support = Group.objects.get(name=ROLE_GROUP[Role.SUPPORT])
    admin = Group.objects.get(name=ROLE_GROUP[Role.ADMIN])

    assert p_fulfill in ops.permissions.all()
    assert p_cancel_admin in support.permissions.all()

    # Admin should have both in MVP
    assert p_fulfill in admin.permissions.all()
    assert p_cancel_admin in admin.permissions.all()


@pytest.mark.django_db
def test_sync_rbac_is_idempotent():
    call_command("sync_rbac")

    # Capture state after first run
    snapshot = {}
    for role, group_name in ROLE_GROUP.items():
        g = Group.objects.get(name=group_name)
        snapshot[group_name] = set(g.permissions.values_list(
            "content_type__app_label", "codename"))

    # Second run should not change assignments
    call_command("sync_rbac")

    for group_name, perms_before in snapshot.items():
        g = Group.objects.get(name=group_name)
        perms_after = set(g.permissions.values_list(
            "content_type__app_label", "codename"))
        assert perms_after == perms_before


@pytest.mark.django_db
def test_sync_rbac_dry_run_does_not_mutate_db():
    # Remove managed groups to make mutation visible
    Group.objects.filter(name__in=set(ROLE_GROUP.values())).delete()
    assert Group.objects.filter(name__in=set(ROLE_GROUP.values())).count() == 0

    # dry_run must not create groups
    call_command("sync_rbac", dry_run=True)

    assert Group.objects.filter(name__in=set(ROLE_GROUP.values())).count() == 0


@pytest.mark.django_db
def test_sync_rbac_strict_removes_extra_permissions():
    # Ensure baseline exists
    call_command("sync_rbac")

    # Add an extra unrelated permission to ops group
    ops = Group.objects.get(name=ROLE_GROUP[Role.WAREHOUSE_MANAGER])
    extra_perm = Permission.objects.filter(codename="add_user").first()
    assert extra_perm is not None, "Expected built-in permission add_user to exist"
    ops.permissions.add(extra_perm)
    assert extra_perm in ops.permissions.all()

    # strict mode should remove extra perms not declared in ROLE_PERMISSIONS
    call_command("sync_rbac", strict=True)

    ops.refresh_from_db()
    assert extra_perm not in ops.permissions.all()


@pytest.mark.django_db
def test_sync_rbac_fails_fast_if_required_permission_missing():
    """
    If RBAC mapping references a permission string that does not exist in DB,
    sync_rbac should fail with a clear error.

    This simulates accidental mismatch between domain permissions and RBAC registry.
    """
    # We delete one of the required permissions from DB (simulating mismatch).
    ct = ContentType.objects.get_for_model(Order)
    Permission.objects.filter(content_type=ct, codename="can_fulfill").delete()

    # Unit-level: the sync function must raise a specific error type
    with pytest.raises(MissingRBACPermissionsError, match="Missing permissions in DB"):
        sync_rbac()


@pytest.mark.django_db
def test_sync_rbac_management_command_wraps_missing_permissions_as_command_error():
    """
    CLI-level: management command should convert MissingRBACPermissionsError into CommandError
    for proper command UX / non-zero exit code.
    """
    ct = ContentType.objects.get_for_model(Order)
    Permission.objects.filter(content_type=ct, codename="can_fulfill").delete()

    with pytest.raises(CommandError, match="Missing permissions in DB"):
        call_command("sync_rbac")
