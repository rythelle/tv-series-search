from dataclasses import dataclass, field

from domain.errors import CommentTooLong, EmptyComment

DEFAULT_MAX_LENGTH = 1000


@dataclass(frozen=True)
class CommentBody:
    value: str
    max_length: int = field(default=DEFAULT_MAX_LENGTH)

    def __post_init__(self):
        trimmed = self.value.strip()
        if not trimmed:
            raise EmptyComment("comment body is empty after trimming")
        if len(trimmed) > self.max_length:
            raise CommentTooLong(len(trimmed), self.max_length)
        object.__setattr__(self, "value", trimmed)
