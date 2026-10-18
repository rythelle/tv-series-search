from datetime import datetime

import asyncpg

from application.interfaces.insight_cache import InsightCache
from domain.entities.insight import Insight
from domain.value_objects.insight_text import InsightText


class PostgresInsightCache(InsightCache):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get(self, cache_key: str) -> Insight | None:
        sql = """
            SELECT text, source, model, created_at FROM insight_cache
            WHERE cache_key = $1 AND expires_at > now()
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, cache_key)
        if row is None:
            return None
        return Insight(
            text=InsightText(row["text"]), source=row["source"], model=row["model"],
            generated_at=row["created_at"],
        )

    async def set(
        self, cache_key: str, target_type: str, target_id: int, insight: Insight, expires_at: datetime,
    ) -> None:
        sql = """
            INSERT INTO insight_cache (cache_key, target_type, target_id, text, source, model, created_at, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (cache_key) DO UPDATE SET
                target_type = EXCLUDED.target_type, target_id = EXCLUDED.target_id,
                text = EXCLUDED.text, source = EXCLUDED.source, model = EXCLUDED.model,
                created_at = EXCLUDED.created_at, expires_at = EXCLUDED.expires_at
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                sql, cache_key, target_type, target_id, insight.text.value, insight.source,
                insight.model, insight.generated_at, expires_at,
            )

    async def invalidate_for_target(self, target_type: str, target_id: int) -> None:
        sql = "DELETE FROM insight_cache WHERE target_type = $1 AND target_id = $2"
        async with self._pool.acquire() as conn:
            await conn.execute(sql, target_type, target_id)
