import json

import asyncpg

from infrastructure.messaging.outbox_worker import OutboxEvent, OutboxStore


class PostgresOutboxStore(OutboxStore):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def fetch_unprocessed(self, max_attempts: int, limit: int) -> list[OutboxEvent]:
        sql = """
            SELECT id, type, payload, attempts FROM outbox
            WHERE processed_at IS NULL AND attempts < $1
            ORDER BY id LIMIT $2
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, max_attempts, limit)
        return [
            OutboxEvent(id=row["id"], type=row["type"], payload=json.loads(row["payload"]), attempts=row["attempts"])
            for row in rows
        ]

    async def mark_processed(self, event_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("UPDATE outbox SET processed_at = now() WHERE id = $1", event_id)

    async def record_failure(self, event_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("UPDATE outbox SET attempts = attempts + 1 WHERE id = $1", event_id)
