from __future__ import annotations
from rest_framework.permissions import BasePermission


def require_staff_or_perm(required_perm: str) -> type[BasePermission]:
    """Factory for DRF permission classes.

    DRF instantiates permission classes without init arguments when used in
    `permission_classes = [...]`. This factory returns a concrete BasePermission
    subclass bound to a specific Django permission string.

    MVP behavior:
    - Deny unauthenticated requests
    - Allow superusers
    - Allow staff users (MVP fallback)
    - Allow users who have the specific Django permission (including via Group)
    """

    class _IsStaffOrHasDjangoPerm(BasePermission):
        message = "You do not have permission to perform this action."

        def has_permission(self, request, view) -> bool:
            user = getattr(request, "user", None)
            if not user or not user.is_authenticated:
                return False
            if user.is_superuser:
                return True
            if user.is_staff:
                return True
            return user.has_perm(required_perm)

    return _IsStaffOrHasDjangoPerm
