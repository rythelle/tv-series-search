from datetime import datetime, timezone

import pytest

from application.dto.comment_dto import PostCommentInput
from application.use_cases.post_comment import PostComment
from domain.errors import CommentTooLong, EmptyComment
from tests.fakes.clock import FakeClock
from tests.fakes.comment_fakes import FakeCommentRepository, FakeEventPublisher, FakeUnitOfWork

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
VIEWER = "3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10"


def _use_case():
    comments = FakeCommentRepository()
    events = FakeEventPublisher()
    uow = FakeUnitOfWork(comments, events)
    use_case = PostComment(unit_of_work_factory=lambda: uow, clock=FakeClock(NOW))
    return use_case, comments, events, uow


async def test_persists_the_comment_and_publishes_an_event_then_commits():
    use_case, comments, events, uow = _use_case()

    created = await use_case.execute(
        PostCommentInput(target_type="show", target_id=1, viewer_id=VIEWER, body="Great show!")
    )

    assert created.id == 1
    assert created.created_at == NOW
    assert len(comments.comments) == 1
    assert len(events.published) == 1
    assert events.published[0].comment_id == 1
    assert uow.committed is True


async def test_rejects_an_empty_body():
    use_case, *_ = _use_case()

    with pytest.raises(EmptyComment):
        await use_case.execute(
            PostCommentInput(target_type="show", target_id=1, viewer_id=VIEWER, body="   ")
        )


async def test_rejects_a_body_over_the_max_length():
    use_case, *_ = _use_case()

    with pytest.raises(CommentTooLong):
        await use_case.execute(
            PostCommentInput(target_type="show", target_id=1, viewer_id=VIEWER, body="x" * 1001)
        )
