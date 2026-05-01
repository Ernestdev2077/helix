"""AgentRun + AgentEvent — trace of LangGraph executions."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.workspaces.models import TimestampedModel


class AgentRun(TimestampedModel):
    """A single execution of an agent graph (e.g. content generation)."""

    class Kind(models.TextChoices):
        CONTENT = "content", "Content generation"
        AB_VARIATION = "ab_variation", "A/B refine — variations of a winner"
        REFERENCE_DNA = "reference_dna", "Reference DNA extraction"
        CURATION = "curation", "Curator — style rules"
        ANALYSIS = "analysis", "Analyst — insights"
        EDIT = "edit", "Inline edit (Cmd+K)"
        BRAND_VOICE = "brand_voice", "Brand voice extraction"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting human approval"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="agent_runs"
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.QUEUED)

    post = models.ForeignKey(
        "content.Post",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_runs",
    )

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    total_tokens_in = models.IntegerField(default=0)
    total_tokens_out = models.IntegerField(default=0)
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    langsmith_trace_id = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["post", "status"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.kind} {self.id} [{self.status}]"


class AgentEvent(TimestampedModel):
    """An event emitted during an ``AgentRun`` — used for the UI timeline."""

    class Kind(models.TextChoices):
        NODE_STARTED = "node_started", "Node started"
        NODE_FINISHED = "node_finished", "Node finished"
        LLM_CALL = "llm_call", "LLM call"
        TOOL_CALL = "tool_call", "Tool call"
        STREAM_CHUNK = "stream_chunk", "Stream chunk"
        STATE_UPDATE = "state_update", "State update"
        HUMAN_INPUT_REQUIRED = "human_input_required", "Human input required"
        ERROR = "error", "Error"
        INFO = "info", "Info"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="events")
    sequence = models.IntegerField(help_text="Monotonic order within a run")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    node_name = models.CharField(max_length=80, blank=True)

    message = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)

    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    duration_ms = models.IntegerField(default=0)

    class Meta:
        ordering = ["run_id", "sequence"]
        unique_together = ("run", "sequence")
        indexes = [models.Index(fields=["run", "sequence"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.run_id}#{self.sequence} {self.kind}"
