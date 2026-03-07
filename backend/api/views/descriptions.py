"""
Martor markdown image upload endpoint.

Handles file uploads triggered by the Martor editor (product descriptions).
Images are stored under MARTOR_UPLOAD_PATH via the configured default storage,
so swapping to S3 or any other backend requires only a settings change.
"""

import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.views import APIView


# Permitted MIME types and extensions for description images.
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Maximum accepted file size in bytes (5 MiB).
_MAX_FILE_SIZE = 5 * 1024 * 1024


class MartorImageUploadView(APIView):
    """
    POST /api/v1/descriptions/upload/

    Accepts a single image file in the ``markdown-image-upload`` field and
    saves it to ``settings.MARTOR_UPLOAD_PATH`` via ``default_storage``.
    Returns ``{"link": "<storage url>"}`` on success, compatible with the
    Martor editor's expected response format.

    Access: authenticated staff/admin users only.
    No database model is created for the uploaded image.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        upload = request.FILES.get("markdown-image-upload")
        if not upload:
            return JsonResponse({"error": "No file provided."}, status=400)

        # Validate MIME type reported by the client.
        if upload.content_type not in _ALLOWED_CONTENT_TYPES:
            return JsonResponse(
                {"error": "Unsupported file type. Allowed: jpg, jpeg, png, webp."},
                status=400,
            )

        # Validate file extension.
        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in _ALLOWED_EXTENSIONS:
            return JsonResponse(
                {"error": "Unsupported file extension. Allowed: jpg, jpeg, png, webp."},
                status=400,
            )

        # Validate file size.
        if upload.size > _MAX_FILE_SIZE:
            return JsonResponse(
                {"error": "File too large. Maximum allowed size is 5 MB."},
                status=400,
            )

        # Build a collision-resistant storage path.
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        upload_path = getattr(settings, "MARTOR_UPLOAD_PATH", "products/descriptions")
        relative_path = os.path.join(upload_path, unique_filename)

        # Persist via the configured default storage backend.
        saved_path = default_storage.save(relative_path, upload)
        storage_url = default_storage.url(saved_path)

        return JsonResponse({"link": storage_url})
