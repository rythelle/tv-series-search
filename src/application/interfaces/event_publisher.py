from abc import ABC, abstractmethod

from application.events import CommentPosted


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: CommentPosted) -> None: ...
