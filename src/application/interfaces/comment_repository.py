from abc import ABC, abstractmethod

from domain.entities.comment import Comment


class CommentRepository(ABC):
    @abstractmethod
    async def add(self, comment: Comment) -> Comment: ...

    @abstractmethod
    async def list_for_target(self, target_type: str, target_id: int, limit: int) -> list[Comment]: ...

    @abstractmethod
    async def fingerprint(self, target_type: str, target_id: int) -> tuple[int, int]: ...
