from django.contrib.auth import authenticate, login
from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema

from api.serializers.auth import LoginRequestSerializer


class LoginView(APIView):
    authentication_classes = []  # allow unauthenticated
    permission_classes = []

    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: None},
        summary="Login user (test endpoint)",
        description=(
            "Login endpoint intended for automated testing and QA workflows. "
            "Creates a session and sets authentication cookies."
        ),
        tags=["Auth"],
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            raise ValidationError("Invalid username or password")

        login(request, user)

        return Response({"detail": "Login successful"})


class CsrfTokenView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        responses={200: None},
        summary="Get CSRF token (test helper)",
        description="Returns CSRF token cookie for authenticated requests.",
        tags=["Auth"],
    )
    def get(self, request):
        get_token(request)
        return Response({"detail": "CSRF cookie set"})
