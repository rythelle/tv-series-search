from datetime import datetime, timedelta, timezone

from infrastructure.resilience.token_bucket_rate_limiter import TokenBucketRateLimiter
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def test_allows_requests_up_to_the_limit():
    limiter = TokenBucketRateLimiter(FakeClock(NOW))

    decisions = [await limiter.allow("viewer-1", limit_per_minute=3) for _ in range(3)]

    assert all(d.allowed for d in decisions)


async def test_rejects_once_the_bucket_is_empty():
    limiter = TokenBucketRateLimiter(FakeClock(NOW))
    for _ in range(3):
        await limiter.allow("viewer-1", limit_per_minute=3)

    decision = await limiter.allow("viewer-1", limit_per_minute=3)

    assert decision.allowed is False
    assert decision.retry_after_seconds >= 1


async def test_refills_over_time():
    clock = FakeClock(NOW)
    limiter = TokenBucketRateLimiter(clock)
    for _ in range(3):
        await limiter.allow("viewer-1", limit_per_minute=3)

    clock.set(NOW + timedelta(seconds=20))  # 3/min refills 1 token every 20s

    assert (await limiter.allow("viewer-1", limit_per_minute=3)).allowed is True


async def test_tracks_separate_buckets_per_key():
    limiter = TokenBucketRateLimiter(FakeClock(NOW))
    for _ in range(3):
        await limiter.allow("viewer-1", limit_per_minute=3)

    assert (await limiter.allow("viewer-2", limit_per_minute=3)).allowed is True
