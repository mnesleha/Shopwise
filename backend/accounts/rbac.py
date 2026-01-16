from django.contrib.auth.models import Group, Permission
from django.db import transaction
from api.exceptions.accounts import MissingRBACPermissionsError

from accounts.permissions import (
    ORDERS_CAN_FULFILL,
    ORDERS_CAN_CANCEL_ADMIN,
)
from accounts.roles import Role

# NOTE:
# Role values are stable identifiers used in seed data and documentation.
# Group names are technical buckets for permissions and may intentionally differ
# from role identifiers (e.g., warehouse_manager -> ops_fulfillment).

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


def _resolve_required_permissions() -> dict[str, Permission]:
    """Resolve permission strings to Permission objects.

    Raises:
        MissingRBACPermissionsError: if any referenced permissions are missing in DB.
    """

    required_perms: set[str] = set()
    for perms in ROLE_PERMISSIONS.values():
        required_perms.update(perms)

    missing: list[str] = []
    perm_objects: dict[str, Permission] = {}

    for perm in required_perms:
        app_label, codename = _parse_perm(perm)
        permission = Permission.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
        ).first()
        if not permission:
            missing.append(perm)
        else:
            perm_objects[perm] = permission

    if missing:
        raise MissingRBACPermissionsError(
            f"Missing permissions in DB: {', '.join(sorted(missing))}"
        )

    return perm_objects


def sync_rbac(*, dry_run: bool = False, strict: bool = False) -> dict:
    """Sync RBAC groups and permissions from ROLE_GROUP / ROLE_PERMISSIONS.

    - Idempotent: safe to run repeatedly.
    - dry_run=True: compute and return a plan, but do not mutate the DB.
    - strict=True: remove permissions not declared in ROLE_PERMISSIONS from managed groups.

    Returns a summary dict:
        created_groups: list[str]
        updated_groups: list[str]
        removed_perms: dict[group_name, list["app_label.codename"]]

    Raises:
        MissingRBACPermissionsError: if referenced permissions do not exist in DB.
    """

    created_groups: list[str] = []
    updated_groups: list[str] = []
    removed_perms: dict[str, list[str]] = {}

    perm_objects = _resolve_required_permissions()

    # Build a plan first (same logic for dry-run and real run)
    plan = []
    for role, group_name in ROLE_GROUP.items():
        desired = {perm_objects[p] for p in ROLE_PERMISSIONS[role]}

        group = Group.objects.filter(name=group_name).first()
        group_exists = group is not None
        current = set(group.permissions.all()) if group_exists else set()

        to_add = desired - current
        to_remove = (current - desired) if (strict and group_exists) else set()

        plan.append(
            {
                "group_name": group_name,
                "group_exists": group_exists,
                "to_add": to_add,
                "to_remove": to_remove,
            }
        )

        # Summary should represent what would happen on a real run
        if not group_exists:
            created_groups.append(group_name)
        if (not group_exists) or to_add or to_remove:
            updated_groups.append(group_name)
        if to_remove:
            removed_perms[group_name] = [
                f"{p.content_type.app_label}.{p.codename}" for p in to_remove
            ]

    if dry_run:
        return {
            "created_groups": created_groups,
            "updated_groups": updated_groups,
            "removed_perms": removed_perms,
        }

    with transaction.atomic():
        for item in plan:
            group_name: str = item["group_name"]
            to_add = item["to_add"]
            to_remove = item["to_remove"]

            group, _ = Group.objects.get_or_create(name=group_name)

            if to_add:
                group.permissions.add(*to_add)
            if to_remove:
                group.permissions.remove(*to_remove)

    return {
        "created_groups": created_groups,
        "updated_groups": updated_groups,
        "removed_perms": removed_perms,
    }
