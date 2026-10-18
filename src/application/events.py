from dataclasses import dataclass


@dataclass(frozen=True)
class CommentPosted:
    comment_id: int
    target_type: str
    target_id: int
