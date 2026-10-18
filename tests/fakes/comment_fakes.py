from dataclasses import replace

from application.interfaces.comment_repository import CommentRepository
from application.interfaces.event_publisher import EventPublisher
from application.interfaces.unit_of_work import UnitOfWork
from domain.entities.comment import Comment


class FakeCommentRepository(CommentRepository):
    def __init__(self, comments: list[Comment] | None = None):
        self._next_id = 1
        self.comments: list[Comment] = list(comments or [])

    async def add(self, comment: Comment) -> Comment:
        created = replace(comment, id=self._next_id)
        self._next_id += 1
        self.comments.append(created)
        return created

    async def list_for_target(self, target_type: str, target_id: int, limit: int) -> list[Comment]:
        matches = [
            c for c in self.comments if c.target_type == target_type and c.target_id == target_id
        ]
        return sorted(matches, key=lambda c: c.created_at, reverse=True)[:limit]

    async def fingerprint(self, target_type: str, target_id: int) -> tuple[int, int]:
        matches = [
            c for c in self.comments if c.target_type == target_type and c.target_id == target_id
        ]
        if not matches:
            return (0, 0)
        return (len(matches), max(c.id for c in matches))


class FakeEventPublisher(EventPublisher):
    def __init__(self):
        self.published = []

    async def publish(self, event) -> None:
        self.published.append(event)


class FakeUnitOfWork(UnitOfWork):
    def __init__(self, comments: CommentRepository, events: EventPublisher):
        self.comments = comments
        self.events = events
        self.committed = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True
