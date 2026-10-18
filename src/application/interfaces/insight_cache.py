from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.insight import Insight


class InsightCache(ABC):
    @abstractmethod
    async def get(self, cache_key: str) -> Insight | None: ...

    @abstractmethod
    async def set(
        self, cache_key: str, target_type: str, target_id: int, insight: Insight, expires_at: datetime,
    ) -> None: ...

    @abstractmethod
    async def invalidate_for_target(self, target_type: str, target_id: int) -> None: ...
