from api.exceptions.base import InternalServerException


class MissingRBACPermissionsError(InternalServerException):
    """
    Raised when RBAC registry references permissions that are missing in the DB.
    Typically indicates missing migrations or a misconfigured environment.
    """

    default_code = "MISSING_RBAC_PERMISSIONS"
    default_detail = "Missing RBAC permissions in DB."
