"""KB document ingest pipeline.

Synchronous for now — small docs (<10k chars) take ~2-5 seconds end-to-end
which is fine inside a request. We will move to Celery once people start
uploading bigger files.

Pipeline:
    KBDocument(raw_text) -> _chunk_text() -> [Chunk]
                         -> _embed_batch() -> [vector]
                         -> bulk-insert KBChunk rows
                         -> KBDocument.status = READY
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import httpx

from apps.brands.models import EMBEDDING_DIM, KBChunk, KBDocument

log = logging.getLogger(__name__)


@dataclass
class _Chunk:
    text: str


# ---------------------------------------------------------------------------
# Chunking — paragraph-aware with a target size
# ---------------------------------------------------------------------------
_PARAGRAPH_RE = re.compile(r"\n\s*\n")


def _approx_tokens(s: str) -> int:
    # Rough heuristic: ~0.75 token / word.
    return max(1, int(len(s.split()) * 1.3))


def _chunk_text(text: str, *, target_tokens: int = 400, overlap_tokens: int = 60) -> list[_Chunk]:
    """Split text on blank lines, then pack paragraphs into target-sized chunks.

    If a single paragraph is bigger than the target it gets force-split on
    sentence boundaries.
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in _PARAGRAPH_RE.split(text) if p.strip()]
    chunks: list[_Chunk] = []
    buf: list[str] = []
    buf_tokens = 0

    def _flush():
        nonlocal buf, buf_tokens
        if buf:
            chunks.append(_Chunk(text="\n\n".join(buf)))
            buf = []
            buf_tokens = 0

    for p in paragraphs:
        p_tokens = _approx_tokens(p)
        if p_tokens > target_tokens:
            # Force-split big paragraph on sentence boundaries
            _flush()
            sentences = re.split(r"(?<=[.!?])\s+", p)
            sub: list[str] = []
            sub_tokens = 0
            for s in sentences:
                t = _approx_tokens(s)
                if sub_tokens + t > target_tokens and sub:
                    chunks.append(_Chunk(text=" ".join(sub).strip()))
                    sub = []
                    sub_tokens = 0
                sub.append(s)
                sub_tokens += t
            if sub:
                chunks.append(_Chunk(text=" ".join(sub).strip()))
            continue

        if buf_tokens + p_tokens > target_tokens and buf:
            _flush()
        buf.append(p)
        buf_tokens += p_tokens

    _flush()

    # Add overlap to mitigate context loss between chunks
    if overlap_tokens and len(chunks) > 1:
        with_overlap: list[_Chunk] = [chunks[0]]
        for prev, cur in zip(chunks, chunks[1:]):
            tail_words = prev.text.split()[-overlap_tokens:]
            tail = " ".join(tail_words)
            with_overlap.append(_Chunk(text=f"{tail}\n\n{cur.text}"))
        chunks = with_overlap

    return chunks


# ---------------------------------------------------------------------------
# Embeddings — OpenRouter (or fallback OpenAI direct) via httpx
# ---------------------------------------------------------------------------
def _has_embedding_key() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"))


def _embedding_endpoint_and_headers() -> tuple[str, dict[str, str], str]:
    """Pick the embedding provider available. Returns (url, headers, model_name)."""
    if os.getenv("OPENROUTER_API_KEY"):
        return (
            "https://openrouter.ai/api/v1/embeddings",
            {
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Ernestdev2077/helix",
                "X-Title": "helix",
            },
            "openai/text-embedding-3-small",
        )
    return (
        "https://api.openai.com/v1/embeddings",
        {
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        "text-embedding-3-small",
    )


def _embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if not _has_embedding_key():
        # Deterministic-ish stub vector so we still create rows. Hashes the text
        # and projects to the right dimension. Good enough to keep dev unblocked
        # but obviously not searchable in any meaningful way.
        log.warning("No embedding API key — returning stub vectors")
        return [_stub_vector(t) for t in texts]

    url, headers, model = _embedding_endpoint_and_headers()
    payload = {"model": model, "input": texts}
    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    embeddings = [item["embedding"] for item in data.get("data", [])]
    if len(embeddings) != len(texts):
        raise RuntimeError(f"Embedding count mismatch: got {len(embeddings)}, expected {len(texts)}")
    return embeddings


def _stub_vector(text: str) -> list[float]:
    import hashlib

    h = hashlib.sha256(text.encode()).digest()
    # Tile the 32 bytes to fill EMBEDDING_DIM and normalize to [-1, 1]
    floats = [(h[i % len(h)] - 128) / 128.0 for i in range(EMBEDDING_DIM)]
    return floats


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ingest_document(doc: KBDocument) -> int:
    """Chunk + embed + persist KBChunks for one document. Idempotent.

    Returns the number of chunks created (re-creates from scratch on re-run).
    Updates the document's status and token_count.
    """
    if not doc.raw_text:
        doc.status = KBDocument.Status.FAILED
        doc.error_message = "Empty raw_text"
        doc.save(update_fields=["status", "error_message", "updated_at"])
        return 0

    doc.status = KBDocument.Status.PROCESSING
    doc.error_message = ""
    doc.save(update_fields=["status", "error_message", "updated_at"])

    KBChunk.objects.filter(document=doc).delete()

    chunks = _chunk_text(doc.raw_text)
    if not chunks:
        doc.status = KBDocument.Status.READY
        doc.token_count = 0
        doc.save(update_fields=["status", "token_count", "updated_at"])
        return 0

    try:
        vectors = _embed_batch([c.text for c in chunks])
    except Exception as exc:  # noqa: BLE001
        log.exception("Embedding failed for doc %s", doc.id)
        doc.status = KBDocument.Status.FAILED
        doc.error_message = str(exc)[:500]
        doc.save(update_fields=["status", "error_message", "updated_at"])
        return 0

    rows = []
    total_tokens = 0
    for i, (chunk, emb) in enumerate(zip(chunks, vectors)):
        rows.append(KBChunk(
            document=doc,
            brand=doc.brand,
            position=i,
            text=chunk.text,
            embedding=emb,
            token_count=_approx_tokens(chunk.text),
        ))
        total_tokens += _approx_tokens(chunk.text)
    KBChunk.objects.bulk_create(rows)

    doc.status = KBDocument.Status.READY
    doc.token_count = total_tokens
    doc.save(update_fields=["status", "token_count", "updated_at"])

    return len(rows)
