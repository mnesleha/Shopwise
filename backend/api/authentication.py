from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    def get_header(self, request):
        header = super().get_header(request)
        if header:
            return header

        token = request.COOKIES.get(getattr(settings, "AUTH_COOKIE_ACCESS", "access_token"))
        if not token:
            return None
        return f"Bearer {token}".encode("utf-8")

    def get_user(self, validated_token):
        """
        Extend the base implementation with a token_version (tv) claim check.

        The base class already fetches the user from the DB, so this adds no
        extra queries.  If the access token's tv claim is stale (i.e. the user
        called logout-all or changed their email since the token was issued),
        every subsequent authenticated request is immediately rejected with 401
        rather than waiting for the access token to naturally expire.

        Access tokens without a tv claim (issued before this feature or by
        third-party clients) are allowed through unchanged to preserve backward
        compatibility during a rolling deploy.
        """
        user = super().get_user(validated_token)

        tv_claim = validated_token.get("tv")
        if tv_claim is None:
            # Legacy token without tv claim — allow to preserve backward compat.
            return user

        if user.token_version != tv_claim:
            raise AuthenticationFailed(
                detail="Session has been revoked. Please log in again.",
                code="SESSION_REVOKED",
            )

        return user