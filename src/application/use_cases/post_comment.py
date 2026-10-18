from collections.abc import Callable

from application.dto.comment_dto import PostCommentInput
from application.events import CommentPosted
from application.interfaces.clock import Clock
from application.interfaces.unit_of_work import UnitOfWork
from domain.entities.comment import Comment
from domain.value_objects.comment_body import CommentBody
from domain.value_objects.viewer_id import ViewerId


class PostComment:
    def __init__(self, unit_of_work_factory: Callable[[], UnitOfWork], clock: Clock):
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def execute(self, input: PostCommentInput) -> Comment:
        comment = Comment(
            id=None,
            target_type=input.target_type,
            target_id=input.target_id,
            viewer_id=ViewerId(input.viewer_id),
            body=CommentBody(input.body),
            created_at=self._clock.now(),
        )

        async with self._unit_of_work_factory() as unit_of_work:
            created = await unit_of_work.comments.add(comment)
            await unit_of_work.events.publish(
                CommentPosted(
                    comment_id=created.id,
                    target_type=created.target_type,
                    target_id=created.target_id,
                )
            )
            await unit_of_work.commit()

        return created
