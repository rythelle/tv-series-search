import json

import asyncpg

from application.events import CommentPosted
from application.interfaces.clock import Clock
from application.interfaces.event_publisher import EventPublisher


class PostgresOutboxPublisher(EventPublisher):
    def __init__(self, connection: asyncpg.Connection, clock: Clock):
        self._connection = connection
        self._clock = clock

    async def publish(self, event: CommentPosted) -> None:
        payload = json.dumps(
            {
                "comment_id": event.comment_id,
                "target_type": event.target_type,
                "target_id": event.target_id,
            }
        )
        await self._connection.execute(
            "INSERT INTO outbox (type, payload, created_at) VALUES ($1, $2::jsonb, $3)",
            "CommentPosted", payload, self._clock.now(),
        )
