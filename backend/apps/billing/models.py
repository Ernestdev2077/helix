"""Billing — tracks Stripe subscription state and AI credit usage.

Stripe integration comes later via dj-stripe; this is the minimal shape to
land the schema and let the rest of the app reference it.
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.workspaces.models import TimestampedModel


class Subscription(TimestampedModel):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        UNPAID = "unpaid", "Unpaid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    stripe_subscription_id = models.CharField(max_length=120, blank=True)
    stripe_price_id = models.CharField(max_length=120, blank=True)
    seats = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIALING)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)


class CreditLedger(TimestampedModel):
    """Immutable ledger of AI credit debits and credits."""

    class Kind(models.TextChoices):
        GRANT = "grant", "Granted (monthly reset or purchase)"
        DEBIT = "debit", "Debit (LLM call)"
        ADJUSTMENT = "adjustment", "Adjustment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="credit_ledger"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    amount = models.IntegerField(help_text="In credits — positive for grant, negative for debit")
    agent_run = models.ForeignKey(
        "agent_runs.AgentRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_entries",
    )
    memo = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
