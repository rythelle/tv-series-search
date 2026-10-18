from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from domain.entities.comment import Comment


class PostCommentRequestSchema(BaseModel):
    target_type: Literal["show", "episode"]
    target_id: int
    body: str


class CommentSchema(BaseModel):
    id: int
    target_type: str
    target_id: int
    viewer_id: str
    body: str
    created_at: datetime

    @classmethod
    def from_domain(cls, comment: Comment) -> "CommentSchema":
        return cls(
            id=comment.id, target_type=comment.target_type, target_id=comment.target_id,
            viewer_id=comment.viewer_id.value, body=comment.body.value,
            created_at=comment.created_at,
        )


class CommentsListResponseSchema(BaseModel):
    items: list[CommentSchema]
