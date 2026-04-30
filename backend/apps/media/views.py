"""Media upload + AI generation endpoints."""

from __future__ import annotations

import logging
from io import BytesIO

from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.workspaces.permissions import IsWorkspaceEditor

from .models import MediaAsset
from .serializers import MediaAssetSerializer

log = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}
MAX_UPLOAD_SIZE = 8 * 1024 * 1024  # 8 MB


def _probe_image(file: UploadedFile) -> tuple[int, int]:
    pos = file.tell()
    try:
        chunk = file.read()
        with Image.open(BytesIO(chunk)) as img:
            return img.size
    except Exception:  # noqa: BLE001
        return (0, 0)
    finally:
        file.seek(pos)


class MediaAssetViewSet(viewsets.ReadOnlyModelViewSet):
    """List + retrieve media. Upload via custom action."""

    serializer_class = MediaAssetSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return MediaAsset.objects.none()
        return MediaAsset.objects.filter(workspace=workspace)

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        """Multipart upload — `file` field, optional `brand` and `alt_text`."""
        file: UploadedFile | None = request.FILES.get("file")
        if file is None:
            return Response({"error": "no_file"}, status=status.HTTP_400_BAD_REQUEST)
        if file.content_type not in ALLOWED_MIME_TYPES:
            return Response(
                {"error": "unsupported_type", "mime_type": file.content_type},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"error": "too_large", "max_bytes": MAX_UPLOAD_SIZE, "got": file.size},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        width, height = _probe_image(file)

        brand_id = request.data.get("brand") or None
        alt = request.data.get("alt_text", "") or ""

        asset = MediaAsset(
            workspace=request.workspace,
            brand_id=brand_id,
            uploaded_by=request.user,
            source=MediaAsset.Source.UPLOAD,
            mime_type=file.content_type,
            size_bytes=file.size,
            width=width,
            height=height,
            alt_text=alt[:300],
        )
        asset.file.save(file.name, file, save=False)
        asset.save()

        return Response(
            MediaAssetSerializer(asset, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
