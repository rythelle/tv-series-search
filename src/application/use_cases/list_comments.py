from application.dto.comment_dto import ListCommentsInput
from application.interfaces.comment_repository import CommentRepository
from domain.entities.comment import Comment


class ListComments:
    def __init__(self, repository: CommentRepository):
        self._repository = repository

    async def execute(self, input: ListCommentsInput) -> list[Comment]:
        return await self._repository.list_for_target(input.target_type, input.target_id, input.limit)
