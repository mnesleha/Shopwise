from django.conf import settings
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