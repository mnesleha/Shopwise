from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import Http404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from drf_spectacular.utils import extend_schema

from accounts.services.email_verification import issue_email_verification_token
from api.serializers.dev import (
    DevEmailVerificationTokenRequestSerializer,
    DevEmailVerificationTokenResponseSerializer,
)


class DevEmailVerificationTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Dev Tools"],
        summary="Mint email verification token (DEBUG only)",
        request=DevEmailVerificationTokenRequestSerializer,
        responses={200: DevEmailVerificationTokenResponseSerializer},
    )
    def post(self, request):
        if not settings.DEBUG:
            raise Http404()

        serializer = DevEmailVerificationTokenRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError({"email": ["User not found."]})

        token = issue_email_verification_token(user)
        return Response({"token": token, "email": user.email}, status=200)
