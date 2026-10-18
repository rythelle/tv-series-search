from datetime import datetime, timezone

import pytest

from application.events import CommentPosted
from domain.entities.comment import Comment
from domain.value_objects.comment_body import CommentBody
from domain.value_objects.viewer_id import ViewerId
from infrastructure.persistence.postgres_unit_of_work import PostgresUnitOfWork
from tests.fakes.clock import FakeClock

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
VIEWER = ViewerId("3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10")


def _comment():
    return Comment(
        id=None, target_type="show", target_id=1, viewer_id=VIEWER,
        body=CommentBody("Great show!"), created_at=NOW,
    )


async def test_commit_persists_both_the_comment_and_the_outbox_event(clean_pool):
    uow = PostgresUnitOfWork(clean_pool, FakeClock(NOW))

    async with uow:
        created = await uow.comments.add(_comment())
        await uow.events.publish(CommentPosted(comment_id=created.id, target_type="show", target_id=1))
        await uow.commit()

    async with clean_pool.acquire() as conn:
        comment_count = await conn.fetchval("SELECT count(*) FROM comments")
        outbox_count = await conn.fetchval("SELECT count(*) FROM outbox WHERE type = 'CommentPosted'")
    assert comment_count == 1
    assert outbox_count == 1


async def test_an_exception_before_commit_rolls_back_both_writes(clean_pool):
    uow = PostgresUnitOfWork(clean_pool, FakeClock(NOW))

    with pytest.raises(RuntimeError):
        async with uow:
            created = await uow.comments.add(_comment())
            await uow.events.publish(CommentPosted(comment_id=created.id, target_type="show", target_id=1))
            raise RuntimeError("something failed before commit")

    async with clean_pool.acquire() as conn:
        comment_count = await conn.fetchval("SELECT count(*) FROM comments")
        outbox_count = await conn.fetchval("SELECT count(*) FROM outbox")
    assert comment_count == 0
    assert outbox_count == 0
