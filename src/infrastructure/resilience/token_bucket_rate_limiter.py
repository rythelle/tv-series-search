from dataclasses import dataclass

from application.interfaces.clock import Clock
from application.interfaces.rate_limiter import RateLimitDecision, RateLimiter


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class TokenBucketRateLimiter(RateLimiter):
    def __init__(self, clock: Clock):
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}

    async def allow(self, key: str, limit_per_minute: int) -> RateLimitDecision:
        now = self._clock.now().timestamp()
        bucket = self._buckets.get(key)

        if bucket is None:
            self._buckets[key] = _Bucket(tokens=limit_per_minute - 1, last_refill=now)
            return RateLimitDecision(allowed=True, retry_after_seconds=0)

        refill_rate = limit_per_minute / 60.0
        elapsed = now - bucket.last_refill
        bucket.tokens = min(limit_per_minute, bucket.tokens + elapsed * refill_rate)
        bucket.last_refill = now

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return RateLimitDecision(allowed=True, retry_after_seconds=0)

        seconds_to_next_token = (1 - bucket.tokens) / refill_rate
        return RateLimitDecision(allowed=False, retry_after_seconds=max(1, int(seconds_to_next_token)))
