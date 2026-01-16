from django.contrib.auth.models import Group, Permission
from django.db import transaction

from accounts.permissions import (
    ORDERS_CAN_FULFILL,
    ORDERS_CAN_CANCEL_ADMIN,
)
from accounts.roles import Role


ROLE_GROUP = {
    Role.ADMIN: "admin",
    Role.WAREHOUSE_MANAGER: "ops_fulfillment",
    Role.SUPPORT: "support",
}

ROLE_PERMISSIONS = {
    Role.ADMIN: [ORDERS_CAN_FULFILL, ORDERS_CAN_CANCEL_ADMIN],
    Role.WAREHOUSE_MANAGER: [ORDERS_CAN_FULFILL],
    Role.SUPPORT: [ORDERS_CAN_CANCEL_ADMIN],
}


def _parse_perm(perm: str) -> tuple[str, str]:
    parts = perm.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid permission string: {perm}")
    return parts[0], parts[1]


def sync_rbac(*, dry_run: bool = False, strict: bool = False) -> dict:
    """
    Ensure all RBAC groups exist and have permissions according to ROLE_PERMISSIONS.
    Idempotent. Safe to run repeatedly.
    """
    created_groups = []
    updated_groups = []
    removed_perms = {}
    missing_perms = []

    required_perms = set()
    for perms in ROLE_PERMISSIONS.values():
        required_perms.update(perms)

    perm_objects = {}
    for perm in required_perms:
        app_label, codename = _parse_perm(perm)
        permission = Permission.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
        ).first()
        if not permission:
            missing_perms.append(perm)
        else:
            perm_objects[perm] = permission

    if missing_perms:
        raise Exception(
            f"Missing permissions in DB: {', '.join(sorted(missing_perms))}"
        )

    if dry_run:
        for role, group_name in ROLE_GROUP.items():
            desired = {perm_objects[p] for p in ROLE_PERMISSIONS[role]}
            group = Group.objects.filter(name=group_name).first()
            if not group:
                created_groups.append(group_name)
                updated_groups.append(group_name)
                continue
            current = set(group.permissions.all())
            to_add = desired - current
            to_remove = current - desired if strict else set()
            if to_add or to_remove:
                updated_groups.append(group_name)
            if to_remove:
                removed_perms[group_name] = [
                    f"{p.content_type.app_label}.{p.codename}"
                    for p in to_remove
                ]
        return {
            "created_groups": created_groups,
            "updated_groups": updated_groups,
            "removed_perms": removed_perms,
            "missing_perms": missing_perms,
        }

    with transaction.atomic():
        for role, group_name in ROLE_GROUP.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                created_groups.append(group_name)

            desired = {perm_objects[p] for p in ROLE_PERMISSIONS[role]}
            current = set(group.permissions.all())
            to_add = desired - current
            to_remove = current - desired if strict else set()

            if to_add:
                group.permissions.add(*to_add)
            if to_remove:
                group.permissions.remove(*to_remove)
                removed_perms[group_name] = [
                    f"{p.content_type.app_label}.{p.codename}"
                    for p in to_remove
                ]

            if created or to_add or to_remove:
                updated_groups.append(group_name)

    return {
        "created_groups": created_groups,
        "updated_groups": updated_groups,
        "removed_perms": removed_perms,
        "missing_perms": missing_perms,
    }
