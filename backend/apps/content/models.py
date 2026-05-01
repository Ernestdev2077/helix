"""Content domain — campaigns, posts, A/B variants, references, style rules.

Lifecycle:
    Campaign (optional grouping, e.g. "Feature X launch")
      └─ Post (a logical piece of content, has a brief and a goal)
           ├─ PostVariant (A / B / C — actually-written content per platform)
           │    └─ Publication (the real thing on the platform, with URL and metrics)
           └─ StyleRule / Reference attachments (used by the writer graph)

Learning:
    Reference — a liked / winning post stored as example for few-shot
    StyleRule — declarative rule ("open with a concrete number") proposed by Curator
    WinningPattern — pattern extracted from completed A/B tests
    PromptVersion — versioned prompts for writer agents (prompt evolution)
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.brands.models import EMBEDDING_DIM
from apps.workspaces.models import TimestampedModel


class Platform(models.TextChoices):
    X = "x", "X / Twitter"
    REDDIT = "reddit", "Reddit"
    LINKEDIN = "linkedin", "LinkedIn"


class Campaign(TimestampedModel):
    """A group of related posts around a single launch or theme."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="campaigns"
    )
    brand = models.ForeignKey(
        "brands.Brand", on_delete=models.CASCADE, related_name="campaigns"
    )
    name = models.CharField(max_length=240)
    goal = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["workspace", "status"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Post(TimestampedModel):
    """A single piece of content driven by a user-entered brief.

    A Post can produce multiple ``PostVariant``s (one per platform, possibly
    multiple per platform for A/B). The brief and goals live here; the actual
    written text lives on variants.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        GENERATING = "generating", "Generating"
        REVIEW = "review", "Review"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHED = "published", "Published"
        FAILED = "failed", "Failed"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="posts"
    )
    brand = models.ForeignKey(
        "brands.Brand", on_delete=models.CASCADE, related_name="posts"
    )
    campaign = models.ForeignKey(
        Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )

    brief = models.TextField()
    goals = ArrayField(
        models.CharField(max_length=40), default=list, blank=True,
        help_text="Short tags like: signups, brand, feedback, hire",
    )
    tone_hints = ArrayField(
        models.CharField(max_length=40), default=list, blank=True,
        help_text="Short tags like: ironic, technical, formal, no_emoji",
    )
    target_platforms = ArrayField(
        models.CharField(max_length=20, choices=Platform.choices), default=list
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    pinned_reference_ids = ArrayField(models.UUIDField(), default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["campaign", "status"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Post {self.id} ({self.status})"


class PostVariant(TimestampedModel):
    """An A/B variant of a post for a specific platform."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHED = "published", "Published"
        FAILED = "failed", "Failed"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="variants")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    label = models.CharField(max_length=10, default="A", help_text="A, B, C...")

    content = models.TextField(blank=True)
    media = models.JSONField(
        default=list, blank=True, help_text="[{type: image|video|gif, url, alt}]"
    )

    hook_strategy = models.CharField(
        max_length=40,
        blank=True,
        help_text="Which hook strategy was used: curiosity, controversy, story, ...",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_starred = models.BooleanField(default=False, help_text="User-preferred variant")

    allocation_weight = models.FloatField(
        default=1.0,
        help_text="Relative weight for bandit allocation (updated by Thompson sampling task)",
    )

    critic_notes = models.JSONField(
        default=list, blank=True,
        help_text="Array of {severity, message, fix_suggestion}",
    )

    generated_by_prompt_version = models.ForeignKey(
        "content.PromptVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variants",
    )

    inspired_by_references = models.ManyToManyField(
        "content.Reference", blank=True, related_name="inspired_variants"
    )
    inspired_by_style_rules = models.ManyToManyField(
        "content.StyleRule", blank=True, related_name="inspired_variants"
    )

    class Meta:
        ordering = ["post_id", "platform", "label"]
        unique_together = ("post", "platform", "label")
        indexes = [models.Index(fields=["post", "platform"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.post_id}/{self.platform}/{self.label}"


class Reference(TimestampedModel):
    """A 'liked' reference post — example for few-shot retrieval.

    Sources: paste URL (parser fills platform / raw_text / source_metrics),
    paste text, or auto-import from winning A/B variants.
    """

    class Source(models.TextChoices):
        URL = "url", "URL"
        PASTE = "paste", "Paste"
        WINNER = "winner", "Auto-imported A/B winner"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="references"
    )
    brand = models.ForeignKey(
        "brands.Brand", on_delete=models.CASCADE, related_name="references"
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.URL)
    source_url = models.URLField(blank=True)
    raw_text = models.TextField()
    media = models.JSONField(default=list, blank=True)

    tags = ArrayField(models.CharField(max_length=40), default=list, blank=True)

    # Metrics from the source post (what made us like it)
    source_metrics = models.JSONField(
        default=dict, blank=True,
        help_text="{likes, shares, comments, impressions, captured_at}",
    )

    # Extracted features (length, hook_type, format, tone...) for reranking
    extracted_features = models.JSONField(default=dict, blank=True)

    embedding = VectorField(dimensions=EMBEDDING_DIM, null=True, blank=True)

    likes_count = models.IntegerField(default=0, help_text="Internal likes by team")
    use_count = models.IntegerField(default=0, help_text="Times used as few-shot example")

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "platform"]),
            HnswIndex(
                name="reference_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Reference[{self.platform}] {self.raw_text[:48]}..."


class StyleRule(TimestampedModel):
    """Declarative style rule for a brand, proposed by Curator Agent.

    The user approves / rejects / edits. Approved rules are injected into
    the writer agent's system prompt for that brand / platform.
    """

    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"
        PER_PLATFORM = "platform", "Per platform"
        PER_CAMPAIGN = "campaign", "Per campaign"

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAUSED = "paused", "Paused"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="style_rules"
    )
    brand = models.ForeignKey(
        "brands.Brand", on_delete=models.CASCADE, related_name="style_rules"
    )
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.GLOBAL)
    platform = models.CharField(
        max_length=20, choices=Platform.choices, blank=True, default=""
    )
    campaign = models.ForeignKey(
        Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="style_rules"
    )

    rule_text = models.CharField(max_length=400)
    rationale = models.TextField(blank=True)
    confidence = models.FloatField(default=0.0)

    evidence_references = models.ManyToManyField(
        Reference, blank=True, related_name="supported_rules"
    )
    evidence_winning_patterns = models.ManyToManyField(
        "content.WinningPattern", blank=True, related_name="supported_rules"
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PROPOSED
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    version = models.IntegerField(default=1)
    parent_rule = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["brand", "status"]),
            models.Index(fields=["brand", "scope", "platform"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"StyleRule[{self.scope}] {self.rule_text[:60]}"


class WinningPattern(TimestampedModel):
    """A pattern extracted from completed A/B tests with statistical significance."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="winning_patterns"
    )
    brand = models.ForeignKey(
        "brands.Brand", on_delete=models.CASCADE, related_name="winning_patterns"
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    pattern_text = models.CharField(max_length=400)
    metric = models.CharField(
        max_length=40,
        default="engagement_rate",
        help_text="engagement_rate, ctr, replies, shares...",
    )
    lift = models.FloatField(help_text="Relative lift vs control, e.g. 0.43 for +43%")
    sample_size = models.IntegerField()
    confidence_interval = models.JSONField(default=dict, blank=True)

    evidence_variants = models.ManyToManyField(
        PostVariant, blank=True, related_name="evidenced_patterns"
    )

    promoted_to_rule = models.ForeignKey(
        StyleRule, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["brand", "platform", "-lift"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"WinningPattern[{self.platform}] +{self.lift*100:.0f}% {self.pattern_text[:40]}"


class PromptVersion(TimestampedModel):
    """Versioned prompt for a writer agent — used for prompt evolution and A/B of prompts."""

    class Status(models.TextChoices):
        EXPERIMENTAL = "experimental", "Experimental"
        ACTIVE = "active", "Active"
        DEPRECATED = "deprecated", "Deprecated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="prompt_versions",
        null=True, blank=True,
        help_text="Null for global prompts, set for per-workspace fine-tuned ones",
    )
    agent_name = models.CharField(
        max_length=80, help_text="x_writer, reddit_writer, linkedin_writer, critic..."
    )
    version = models.CharField(max_length=40)
    template = models.TextField()
    parent_version = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.EXPERIMENTAL
    )
    eval_score = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("workspace", "agent_name", "version")
        ordering = ["agent_name", "-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.agent_name}@{self.version} ({self.status})"
