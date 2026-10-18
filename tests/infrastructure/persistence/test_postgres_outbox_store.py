from datetime import datetime, timezone

import pytest

from application.events import CommentPosted
from infrastructure.messaging.postgres_outbox_publisher import PostgresOutboxPublisher
from infrastructure.persistence.postgres_outbox_store import PostgresOutboxStore
from tests.fakes.clock import FakeClock

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def _publish(pool, target_id=1):
    async with pool.acquire() as conn:
        await PostgresOutboxPublisher(conn, FakeClock(NOW)).publish(
            CommentPosted(comment_id=1, target_type="show", target_id=target_id)
        )


async def test_fetch_unprocessed_returns_a_published_event(clean_pool):
    await _publish(clean_pool)
    store = PostgresOutboxStore(clean_pool)

    events = await store.fetch_unprocessed(max_attempts=5, limit=10)

    assert len(events) == 1
    assert events[0].payload["target_id"] == 1


async def test_mark_processed_excludes_it_from_the_next_fetch(clean_pool):
    await _publish(clean_pool)
    store = PostgresOutboxStore(clean_pool)
    event = (await store.fetch_unprocessed(max_attempts=5, limit=10))[0]

    await store.mark_processed(event.id)

    assert await store.fetch_unprocessed(max_attempts=5, limit=10) == []


async def test_record_failure_increments_attempts_until_the_cap(clean_pool):
    await _publish(clean_pool)
    store = PostgresOutboxStore(clean_pool)
    event_id = (await store.fetch_unprocessed(max_attempts=5, limit=10))[0].id

    await store.record_failure(event_id)
    await store.record_failure(event_id)

    assert await store.fetch_unprocessed(max_attempts=2, limit=10) == []
