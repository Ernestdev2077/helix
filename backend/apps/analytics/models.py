"""Analytics — time-series metrics per publication, and bandit state per variant."""

from __future__ import annotations

import uuid

from django.db import models

from apps.workspaces.models import TimestampedModel


class MetricSnapshot(TimestampedModel):
    """Point-in-time snapshot of a Publication's metrics.

    We pull periodically via Celery and append new rows, not mutate — that
    way we keep a time series for trend charts.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="metric_snapshots"
    )
    publication = models.ForeignKey(
        "publishing.Publication", on_delete=models.CASCADE, related_name="metric_snapshots"
    )
    captured_at = models.DateTimeField()

    impressions = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    replies = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)

    raw = models.JSONField(
        default=dict, blank=True,
        help_text="Full platform response for reference and future re-computation",
    )

    class Meta:
        ordering = ["-captured_at"]
        indexes = [
            models.Index(fields=["publication", "-captured_at"]),
            models.Index(fields=["workspace", "-captured_at"]),
        ]


class BanditArmState(TimestampedModel):
    """Thompson sampling state (Beta distribution) for a variant acting as a bandit arm.

    We use Beta(alpha, beta) where alpha = 1 + successes, beta = 1 + failures.
    For engagement-based allocation: successes = engagements, failures = impressions - engagements.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="bandit_arms"
    )
    variant = models.OneToOneField(
        "content.PostVariant", on_delete=models.CASCADE, related_name="bandit_state"
    )
    campaign = models.ForeignKey(
        "content.Campaign",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bandit_arms",
    )
    alpha = models.FloatField(default=1.0)
    beta = models.FloatField(default=1.0)
    successes = models.IntegerField(default=0)
    trials = models.IntegerField(default=0)
    last_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_updated_at"]
