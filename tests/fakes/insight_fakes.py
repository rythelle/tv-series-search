from datetime import datetime

from application.interfaces.insight_cache import InsightCache
from application.interfaces.insight_generator import InsightGenerator
from domain.entities.insight import Insight


class FakeInsightGenerator(InsightGenerator):
    def __init__(self, insight: Insight | None = None, raises: Exception | None = None):
        self.insight = insight
        self.raises = raises
        self.calls = []

    async def generate(self, context) -> Insight:
        self.calls.append(context)
        if self.raises:
            raise self.raises
        return self.insight


class FakeInsightCache(InsightCache):
    def __init__(self):
        self.store: dict[str, Insight] = {}
        self.targets_by_key: dict[str, tuple[str, int]] = {}
        self.sets: list[tuple[str, str, int, Insight, datetime]] = []
        self.invalidated: list[tuple[str, int]] = []

    async def get(self, cache_key: str) -> Insight | None:
        return self.store.get(cache_key)

    async def set(
        self, cache_key: str, target_type: str, target_id: int, insight: Insight, expires_at: datetime,
    ) -> None:
        self.store[cache_key] = insight
        self.targets_by_key[cache_key] = (target_type, target_id)
        self.sets.append((cache_key, target_type, target_id, insight, expires_at))

    async def invalidate_for_target(self, target_type: str, target_id: int) -> None:
        self.invalidated.append((target_type, target_id))
        self.store = {
            key: insight
            for key, insight in self.store.items()
            if self.targets_by_key.get(key) != (target_type, target_id)
        }
