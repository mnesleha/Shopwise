from rest_framework.permissions import BasePermission


class IsStaffOrHasDjangoPerm(BasePermission):
    def __init__(self, required_perm: str):
        self.required_perm = required_perm

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user.is_staff:
            return True
        return user.has_perm(self.required_perm)
