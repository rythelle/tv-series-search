from datetime import datetime, timezone

from application.dto.comment_dto import ListCommentsInput
from application.use_cases.list_comments import ListComments
from domain.entities.comment import Comment
from domain.value_objects.comment_body import CommentBody
from domain.value_objects.viewer_id import ViewerId
from tests.fakes.comment_fakes import FakeCommentRepository

VIEWER = ViewerId("3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10")


def _comment(comment_id, target_id, created_at):
    return Comment(
        id=comment_id, target_type="show", target_id=target_id, viewer_id=VIEWER,
        body=CommentBody("hi"), created_at=created_at,
    )


async def test_returns_comments_for_the_target_newest_first():
    repo = FakeCommentRepository(
        comments=[
            _comment(1, 1, datetime(2026, 1, 1, tzinfo=timezone.utc)),
            _comment(2, 1, datetime(2026, 1, 2, tzinfo=timezone.utc)),
            _comment(3, 2, datetime(2026, 1, 3, tzinfo=timezone.utc)),
        ]
    )
    use_case = ListComments(repository=repo)

    result = await use_case.execute(ListCommentsInput(target_type="show", target_id=1, limit=50))

    assert [c.id for c in result] == [2, 1]
