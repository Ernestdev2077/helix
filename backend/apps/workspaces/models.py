"""Workspace / tenant models.

A ``Workspace`` is the tenant root — every piece of content, brand, billing
record, etc. belongs to exactly one workspace. Users join workspaces via
``Membership`` with a specific role, and ``Invite`` represents a pending
invitation by email.
"""

from __future__ import annotations

import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def _default_invite_token() -> str:
    return secrets.token_urlsafe(32)


class TimestampedModel(models.Model):
    """Abstract base with created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class WorkspaceScopedModel(TimestampedModel):
    """Abstract base for any model that belongs to a workspace."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="+",
    )

    class Meta:
        abstract = True


class Workspace(TimestampedModel):
    """Top-level tenant boundary."""

    class Plan(models.TextChoices):
        FREE = "free", "Free"
        STARTER = "starter", "Starter"
        PRO = "pro", "Pro"
        TEAM = "team", "Team"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=60, unique=True)

    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=120, blank=True)

    ai_credits_monthly = models.IntegerField(default=100_000)
    ai_credits_used = models.IntegerField(default=0)
    ai_credits_reset_at = models.DateTimeField(default=timezone.now)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_workspaces",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.name) or "workspace"
            slug = base
            counter = 1
            while Workspace.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)


class Membership(TimestampedModel):
    """A user's role inside a specific workspace."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EDITOR)

    class Meta:
        unique_together = ("workspace", "user")
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user} in {self.workspace} as {self.role}"


class Invite(TimestampedModel):
    """Pending invitation to join a workspace by email."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="invites"
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=Membership.Role.choices,
        default=Membership.Role.EDITOR,
    )
    token = models.CharField(max_length=64, unique=True, default=_default_invite_token)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("workspace", "email")
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Invite {self.email} → {self.workspace} ({self.status})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
