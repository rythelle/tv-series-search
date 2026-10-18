from dataclasses import dataclass


@dataclass
class PostCommentInput:
    target_type: str
    target_id: int
    viewer_id: str
    body: str


@dataclass
class ListCommentsInput:
    target_type: str
    target_id: int
    limit: int
