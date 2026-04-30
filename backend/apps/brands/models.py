"""Brand, knowledge base, style rules.

A ``Workspace`` can contain multiple ``Brand``s (e.g. an agency managing
several clients). Each brand has its own voice, audience, KB documents,
and learned style rules.

Embeddings are stored via ``pgvector.django.VectorField``. The default
dimension is 1536 to match OpenAI ``text-embedding-3-small``; if you
switch embedding models, create a new column with the right dimension
rather than altering in place (pgvector indexes are dimension-specific).
"""

from __future__ import annotations

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.workspaces.models import TimestampedModel

EMBEDDING_DIM = 1536


class Brand(TimestampedModel):
    """A brand (product / company) within a workspace."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="brands",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=60)
    description = models.TextField(blank=True)

    voice_description = models.TextField(blank=True)
    voice_do = ArrayField(models.CharField(max_length=200), default=list, blank=True)
    voice_dont = ArrayField(models.CharField(max_length=200), default=list, blank=True)

    target_audience = models.TextField(blank=True)
    personas = models.JSONField(default=list, blank=True)

    accent_color = models.CharField(max_length=7, default="#6366F1")
    logo_url = models.URLField(blank=True)

    class Meta:
        unique_together = ("workspace", "slug")
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} [{self.workspace.slug}]"


class KBDocument(TimestampedModel):
    """A single document in a brand's knowledge base.

    Documents are chunked on ingest (see ``apps.brands.services.ingest``)
    and per-chunk embeddings live in ``KBChunk``.
    """

    class SourceType(models.TextChoices):
        UPLOAD = "upload", "Upload"
        URL = "url", "URL"
        PASTE = "paste", "Paste"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=240)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_uri = models.TextField(blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    raw_text = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    token_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.title} ({self.status})"


class KBChunk(TimestampedModel):
    """Embedded chunk of a ``KBDocument`` — used in RAG."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        KBDocument, on_delete=models.CASCADE, related_name="chunks"
    )
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="chunks")
    position = models.IntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIM)
    token_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["document_id", "position"]
        indexes = [
            HnswIndex(
                name="kb_chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            models.Index(fields=["brand", "document"]),
        ]
