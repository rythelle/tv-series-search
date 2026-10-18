from dataclasses import dataclass
from datetime import datetime

from domain.value_objects.comment_body import CommentBody
from domain.value_objects.viewer_id import ViewerId


@dataclass
class Comment:
    id: int | None
    target_type: str
    target_id: int
    viewer_id: ViewerId
    body: CommentBody
    created_at: datetime
