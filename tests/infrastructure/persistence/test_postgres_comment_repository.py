from datetime import datetime, timedelta, timezone

import pytest

from domain.value_objects.viewer_id import ViewerId
from infrastructure.persistence.postgres_comment_repository import PostgresCommentRepository

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
VIEWER = ViewerId("3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10")


async def _add_raw_comment(pool, target_id, created_at):
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO comments (target_type, target_id, viewer_id, body, created_at)
            VALUES ('show', $1, $2, 'Great show!', $3) RETURNING id
            """,
            target_id, VIEWER.value, created_at,
        )


async def test_list_for_target_returns_newest_first(clean_pool):
    await _add_raw_comment(clean_pool, 1, NOW)
    await _add_raw_comment(clean_pool, 1, NOW + timedelta(seconds=1))

    async with clean_pool.acquire() as conn:
        repo = PostgresCommentRepository(conn)
        results = await repo.list_for_target("show", 1, limit=10)

    assert len(results) == 2
    assert results[0].created_at > results[1].created_at


async def test_list_for_target_respects_the_limit(clean_pool):
    for i in range(3):
        await _add_raw_comment(clean_pool, 1, NOW + timedelta(seconds=i))

    async with clean_pool.acquire() as conn:
        repo = PostgresCommentRepository(conn)
        results = await repo.list_for_target("show", 1, limit=2)

    assert len(results) == 2


async def test_fingerprint_reports_count_and_max_id(clean_pool):
    first_id = await _add_raw_comment(clean_pool, 1, NOW)

    async with clean_pool.acquire() as conn:
        repo = PostgresCommentRepository(conn)
        count, max_id = await repo.fingerprint("show", 1)

    assert count == 1
    assert max_id == first_id


async def test_fingerprint_is_zero_for_a_target_with_no_comments(clean_pool):
    async with clean_pool.acquire() as conn:
        repo = PostgresCommentRepository(conn)
        assert await repo.fingerprint("show", 999) == (0, 0)
