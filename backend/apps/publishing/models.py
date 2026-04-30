"""Publishing — platform accounts (OAuth tokens) and Publication records."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.content.models import Platform, PostVariant
from apps.workspaces.models import TimestampedModel


class PlatformAccount(TimestampedModel):
    """Connected social platform account (OAuth tokens + account metadata)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REAUTH_REQUIRED = "reauth_required", "Reauth required"
        REVOKED = "revoked", "Revoked"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="platform_accounts",
    )
    brand = models.ForeignKey(
        "brands.Brand",
        on_delete=models.CASCADE,
        related_name="platform_accounts",
        null=True,
        blank=True,
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)

    external_id = models.CharField(max_length=120, help_text="User ID on the platform")
    handle = models.CharField(max_length=120, blank=True)
    display_name = models.CharField(max_length=240, blank=True)
    avatar_url = models.URLField(blank=True)

    # NOTE: in production, encrypt these (e.g. django-fernet-fields)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        unique_together = ("workspace", "platform", "external_id")
        ordering = ["platform", "-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.platform}:@{self.handle or self.external_id}"


class Publication(TimestampedModel):
    """A single instance of a variant published to a specific platform account."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHING = "publishing", "Publishing"
        PUBLISHED = "published", "Published"
        FAILED = "failed", "Failed"
        DELETED = "deleted", "Deleted"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="publications"
    )
    variant = models.ForeignKey(
        PostVariant, on_delete=models.CASCADE, related_name="publications"
    )
    platform_account = models.ForeignKey(
        PlatformAccount, on_delete=models.PROTECT, related_name="publications"
    )

    scheduled_for = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    external_id = models.CharField(max_length=120, blank=True, help_text="Platform's post ID")
    external_url = models.URLField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-scheduled_for", "-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["scheduled_for", "status"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Publication {self.id} [{self.status}]"
