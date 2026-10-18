from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from application.interfaces.rate_limiter import RateLimitDecision, RateLimiter
from infrastructure.resilience.token_bucket_rate_limiter import TokenBucketRateLimiter
from interface.http.middleware.rate_limit import RateLimitMiddleware
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FixedRateLimiter(RateLimiter):
    def __init__(self, allowed: bool):
        self.allowed = allowed
        self.calls: list[tuple[str, int]] = []

    async def allow(self, key: str, limit_per_minute: int) -> RateLimitDecision:
        self.calls.append((key, limit_per_minute))
        return RateLimitDecision(allowed=self.allowed, retry_after_seconds=0 if self.allowed else 5)


def _app(limiter, requests_per_minute=120, insight_requests_per_minute=10):
    app = FastAPI()

    @app.get("/api/v1/shows/search")
    async def search():
        return {"ok": True}

    @app.post("/api/v1/insights")
    async def insights():
        return {"ok": True}

    @app.get("/api/v1/insights")
    async def peek_insight():
        return {"ok": True}

    app.add_middleware(
        RateLimitMiddleware, rate_limiter=limiter,
        requests_per_minute=requests_per_minute, insight_requests_per_minute=insight_requests_per_minute,
    )
    return app


async def test_allows_the_request_when_the_limiter_allows_it():
    transport = httpx.ASGITransport(app=_app(_FixedRateLimiter(allowed=True)))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/shows/search")
    assert response.status_code == 200


async def test_returns_429_with_retry_after_when_the_limiter_rejects():
    transport = httpx.ASGITransport(app=_app(_FixedRateLimiter(allowed=False)))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/shows/search")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "5"


async def test_uses_the_stricter_limit_for_generating_an_insight():
    limiter = _FixedRateLimiter(allowed=True)
    transport = httpx.ASGITransport(app=_app(limiter))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/v1/insights")
    assert limiter.calls[-1][1] == 10


async def test_uses_the_normal_limit_for_peeking_a_cached_insight():
    limiter = _FixedRateLimiter(allowed=True)
    transport = httpx.ASGITransport(app=_app(limiter))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/insights", params={"target_type": "show", "target_id": 1})
    assert limiter.calls[-1][1] == 120


async def test_keys_by_viewer_id_header_when_present():
    limiter = _FixedRateLimiter(allowed=True)
    transport = httpx.ASGITransport(app=_app(limiter))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/shows/search", headers={"X-Viewer-Id": "viewer-42"})
    assert limiter.calls[-1][0] == "viewer-42"


async def test_the_insight_budget_gets_its_own_bucket():
    # Both limits used to share one bucket per viewer, and the token bucket
    # clamps to the limit it is handed -- so a single insight request dropped
    # that viewer's general allowance from 120 to 10 for the next minute.
    limiter = _FixedRateLimiter(allowed=True)
    transport = httpx.ASGITransport(app=_app(limiter))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Viewer-Id": "viewer-42"}
        await client.post("/api/v1/insights", headers=headers)
        await client.get("/api/v1/shows/search", headers=headers)

    insight_key, insight_limit = limiter.calls[0]
    general_key, general_limit = limiter.calls[1]
    assert (insight_limit, general_limit) == (10, 120)
    assert insight_key != general_key


async def test_a_real_token_bucket_keeps_the_general_allowance_after_an_insight():
    limiter = TokenBucketRateLimiter(FakeClock(NOW))
    transport = httpx.ASGITransport(app=_app(limiter))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Viewer-Id": "viewer-42"}
        await client.post("/api/v1/insights", headers=headers)
        codes = []
        for _ in range(30):
            response = await client.get("/api/v1/shows/search", headers=headers)
            codes.append(response.status_code)

    assert codes == [200] * 30
