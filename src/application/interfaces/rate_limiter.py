from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class RateLimiter(ABC):
    @abstractmethod
    async def allow(self, key: str, limit_per_minute: int) -> RateLimitDecision: ...
