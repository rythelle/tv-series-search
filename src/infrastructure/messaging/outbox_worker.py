import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from application.interfaces.insight_cache import InsightCache


@dataclass
class OutboxEvent:
    id: int
    type: str
    payload: dict
    attempts: int


class OutboxStore(ABC):
    @abstractmethod
    async def fetch_unprocessed(self, max_attempts: int, limit: int) -> list[OutboxEvent]: ...

    @abstractmethod
    async def mark_processed(self, event_id: int) -> None: ...

    @abstractmethod
    async def record_failure(self, event_id: int) -> None: ...


class OutboxWorker:
    def __init__(
        self, store: OutboxStore, insight_cache: InsightCache, poll_interval_seconds: float,
        max_attempts: int, sleep: Callable[[float], Awaitable[None]] | None = None,
    ):
        self._store = store
        self._insight_cache = insight_cache
        self._poll_interval_seconds = poll_interval_seconds
        self._max_attempts = max_attempts
        self._sleep = sleep or asyncio.sleep

    async def process_once(self) -> int:
        events = await self._store.fetch_unprocessed(self._max_attempts, limit=100)
        processed = 0
        for event in events:
            try:
                if event.type == "CommentPosted":
                    await self._insight_cache.invalidate_for_target(
                        event.payload["target_type"], event.payload["target_id"]
                    )
                await self._store.mark_processed(event.id)
                processed += 1
            except Exception:
                await self._store.record_failure(event.id)
        return processed

    async def run_forever(self) -> None:
        while True:
            await self.process_once()
            await self._sleep(self._poll_interval_seconds)
