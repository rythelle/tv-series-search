from abc import ABC, abstractmethod

from application.interfaces.comment_repository import CommentRepository
from application.interfaces.event_publisher import EventPublisher


class UnitOfWork(ABC):
    comments: CommentRepository
    events: EventPublisher

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork": ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...
