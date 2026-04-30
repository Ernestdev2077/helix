"""MediaAsset — uploaded or AI-generated images attached to content.

Files use Django's storage abstraction so we can switch between local
disk (FileSystemStorage in dev) and S3-compatible (R2/MinIO/AWS) in prod
just by changing STORAGES['default'] — no model changes needed.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from apps.workspaces.models import TimestampedModel


def _media_upload_path(instance: "MediaAsset", filename: str) -> str:
    """Path: media/<workspace_id>/<uuid>.<ext> — keeps tenants isolated on disk."""
    ext = Path(filename).suffix.lower() or ".bin"
    return f"workspace/{instance.workspace_id}/{instance.id}{ext}"


class MediaAsset(TimestampedModel):
    class Source(models.TextChoices):
        UPLOAD = "upload", "User upload"
        AI = "ai", "AI generated"
        URL = "url", "Imported by URL"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="media_assets"
    )
    brand = models.ForeignKey(
        "brands.Brand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_assets",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    source = models.CharField(max_length=20, choices=Source.choices, default=Source.UPLOAD)

    file = models.FileField(upload_to=_media_upload_path, max_length=500, blank=True)
    external_url = models.URLField(max_length=1000, blank=True)

    mime_type = models.CharField(max_length=80, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    size_bytes = models.PositiveIntegerField(default=0)

    alt_text = models.CharField(max_length=300, blank=True)
    ai_prompt = models.TextField(blank=True, help_text="Prompt used if AI-generated")
    ai_model = models.CharField(max_length=100, blank=True)
    cost_usd = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["workspace", "source"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"MediaAsset[{self.source}] {self.id}"

    @property
    def url(self) -> str:
        """Best URL to display this asset — works for both local file and external."""
        if self.file:
            return self.file.url
        return self.external_url
