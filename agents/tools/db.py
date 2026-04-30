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
            SELECT id::text, raw_text, platform, tags, likes_count, source_metrics
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
        return [dict(r) for r in rows]


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
            SELECT id::text, platform, raw_text, tags, likes_count
            FROM content_reference
            WHERE workspace_id = $1 AND brand_id = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            workspace_id,
            brand_id,
            limit,
        )
        return [dict(r) for r in rows]
