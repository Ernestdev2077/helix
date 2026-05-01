"""Read-only Postgres queries used by graph nodes.

The agent service has direct DB access (same DATABASE_URL as Django) — this
is the same trust boundary as Django itself. Nodes use these to fetch brand
voice, references, and active style rules without round-tripping through HTTP.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import asyncpg

log = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        url = os.getenv("DATABASE_URL", "postgres://helix:helix_password_change_me@127.0.0.1:5432/helix")
        # asyncpg expects postgres:// or postgresql://, accepts both
        _pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
    assert _pool is not None
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def fetch_brand(brand_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, name, description, voice_description,
                   voice_do, voice_dont, target_audience
            FROM brands_brand WHERE id = $1
            """,
            brand_id,
        )
        return dict(row) if row else None


async def fetch_references(
    *, workspace_id: str, brand_id: str, platform: str, limit: int = 5
) -> list[dict[str, Any]]:
    """Top references for this brand+platform, ordered by likes_count then recency.

    NOTE: real implementation should do hybrid BM25+vector search by brief.
    For now we just take the most-liked refs as a baseline.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, raw_text, platform, tags, likes_count,
                   source_metrics, extracted_features
            FROM content_reference
            WHERE workspace_id = $1
              AND brand_id = $2
              AND (platform = $3 OR platform = '')
            ORDER BY likes_count DESC, created_at DESC
            LIMIT $4
            """,
            workspace_id,
            brand_id,
            platform,
            limit,
        )
        return [_parse_jsonb(dict(r)) for r in rows]


async def fetch_active_rules(
    *, workspace_id: str, brand_id: str, platform: str
) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, scope, platform, rule_text, rationale, confidence
            FROM content_stylerule
            WHERE workspace_id = $1
              AND brand_id = $2
              AND status = 'approved'
              AND (scope = 'global' OR (scope = 'platform' AND platform = $3))
            ORDER BY confidence DESC, created_at DESC
            """,
            workspace_id,
            brand_id,
            platform,
        )
        return [dict(r) for r in rows]


async def fetch_starred_variants(
    *, workspace_id: str, brand_id: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Get content of recently-starred variants — used by Curator as winners."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT v.id::text, v.platform, v.content, v.created_at
            FROM content_postvariant v
            JOIN content_post p ON p.id = v.post_id
            WHERE p.workspace_id = $1 AND p.brand_id = $2 AND v.is_starred = true
            ORDER BY v.created_at DESC
            LIMIT $3
            """,
            workspace_id,
            brand_id,
            limit,
        )
        return [dict(r) for r in rows]


async def fetch_all_references_for_brand(
    *, workspace_id: str, brand_id: str, limit: int = 30
) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, platform, raw_text, tags, likes_count, extracted_features
            FROM content_reference
            WHERE workspace_id = $1 AND brand_id = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            workspace_id,
            brand_id,
            limit,
        )
        return [_parse_jsonb(dict(r)) for r in rows]


async def fetch_winning_patterns(
    *, workspace_id: str, brand_id: str, platform: str
) -> list[dict[str, Any]]:
    """Patterns extracted from past A/B winners. Used by writer in evolution mode."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, platform, pattern_text, metric, lift, sample_size
            FROM content_winningpattern
            WHERE workspace_id = $1
              AND brand_id = $2
              AND (platform = $3 OR platform = '')
            ORDER BY lift DESC, created_at DESC
            LIMIT 10
            """,
            workspace_id,
            brand_id,
            platform,
        )
        return [dict(r) for r in rows]


async def fetch_top_kb_chunks(
    *, workspace_id: str, brand_id: str, query_embedding: list[float], k: int = 3
) -> list[dict[str, Any]]:
    """Cosine-similarity search over KBChunks for one brand. Returns top-k.

    Uses pgvector's `<=>` operator (cosine distance). The vector is sent as a
    bracket-string which pgvector parses; asyncpg has no native vector codec.
    """
    if not query_embedding:
        return []
    vec_literal = "[" + ",".join(f"{x:.6f}" for x in query_embedding) + "]"
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id::text, c.text, c.position,
                   d.title AS document_title,
                   c.embedding <=> $3::vector AS distance
            FROM brands_kbchunk c
            JOIN brands_kbdocument d ON d.id = c.document_id
            WHERE c.brand_id = $1 AND d.brand_id IN (
                SELECT id FROM brands_brand WHERE workspace_id = $2
            )
            ORDER BY c.embedding <=> $3::vector
            LIMIT $4
            """,
            brand_id,
            workspace_id,
            vec_literal,
            k,
        )
        return [dict(r) for r in rows]


async def fetch_brand_dna(
    *, workspace_id: str, brand_id: str
) -> dict[str, Any]:
    """Aggregate writing-DNA across recent references. Returns merged tone /
    structure / hook_patterns or empty dict if there's not enough signal."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT extracted_features
            FROM content_reference
            WHERE workspace_id = $1 AND brand_id = $2
              AND extracted_features IS NOT NULL
              AND extracted_features::text != '{}'
            ORDER BY created_at DESC
            LIMIT 10
            """,
            workspace_id,
            brand_id,
        )
        feats = []
        for r in rows:
            f = r["extracted_features"]
            if isinstance(f, str):
                import json as _json
                try:
                    f = _json.loads(f)
                except Exception:  # noqa: BLE001
                    f = {}
            if isinstance(f, dict):
                feats.append(f)
        if not feats:
            return {}

        # Take the most recent populated values for each axis
        def first_nonempty(key: str) -> str:
            for f in feats:
                v = f.get(key)
                if v:
                    return str(v)
            return ""

        return {
            "tone": first_nonempty("tone"),
            "structure": first_nonempty("structure"),
            "hook_patterns": first_nonempty("hook_patterns"),
            "source_count": len(feats),
        }


async def fetch_winner_cases(
    *, workspace_id: str, brand_id: str, limit: int = 5
) -> list[dict[str, Any]]:
    """Posts where exactly one variant is starred AND there are unstarred siblings.
    Returns: [{brief, winner: {...}, siblings: [...]}, ...]
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH starred_posts AS (
              SELECT DISTINCT p.id, p.brief, p.created_at
              FROM content_post p
              JOIN content_postvariant v ON v.post_id = p.id
              WHERE p.workspace_id = $1 AND p.brand_id = $2 AND v.is_starred = true
              ORDER BY p.created_at DESC
              LIMIT $3
            )
            SELECT sp.id::text AS post_id, sp.brief,
                   v.id::text AS variant_id, v.platform, v.content, v.is_starred, v.label
            FROM starred_posts sp
            JOIN content_postvariant v ON v.post_id = sp.id
            ORDER BY sp.created_at DESC, v.label
            """,
            workspace_id,
            brand_id,
            limit,
        )
        cases: dict[str, dict[str, Any]] = {}
        for r in rows:
            pid = r["post_id"]
            if pid not in cases:
                cases[pid] = {"brief": r["brief"], "winner": None, "siblings": []}
            entry = {
                "id": r["variant_id"],
                "platform": r["platform"],
                "content": r["content"],
                "label": r["label"],
            }
            if r["is_starred"]:
                cases[pid]["winner"] = entry
            else:
                cases[pid]["siblings"].append(entry)
        return [c for c in cases.values() if c["winner"] is not None and c["siblings"]]


async def fetch_variant_for_refine(
    *, variant_id: str
) -> dict[str, Any] | None:
    """Load the content + brand context needed to A/B-refine one variant."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT v.id::text, v.platform, v.content, v.label,
                   p.id::text AS post_id, p.workspace_id::text, p.brand_id::text
            FROM content_postvariant v
            JOIN content_post p ON p.id = v.post_id
            WHERE v.id = $1
            """,
            variant_id,
        )
        return dict(row) if row else None


async def fetch_max_variant_label(*, post_id: str) -> str:
    """Return the highest-letter label currently on a post (e.g. 'C').
    Useful so refine can start writing 'D', 'E', 'F'."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT MAX(label) AS max_label FROM content_postvariant WHERE post_id = $1",
            post_id,
        )
        return (row["max_label"] if row else "") or "A"


def _parse_jsonb(d: dict[str, Any]) -> dict[str, Any]:
    """Some asyncpg rows return JSONB as str; normalize to dict."""
    import json as _json

    for key in ("extracted_features", "source_metrics"):
        if key in d:
            v = d[key]
            if isinstance(v, str):
                try:
                    d[key] = _json.loads(v)
                except Exception:  # noqa: BLE001
                    d[key] = {}
            elif v is None:
                d[key] = {}
    return d
