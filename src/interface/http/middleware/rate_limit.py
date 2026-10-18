from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from application.interfaces.rate_limiter import RateLimiter
from infrastructure.observability.request_context import get_request_id

INSIGHTS_PATH = "/api/v1/insights"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app, rate_limiter: RateLimiter, requests_per_minute: int, insight_requests_per_minute: int,
    ):
        super().__init__(app)
        self._rate_limiter = rate_limiter
        self._requests_per_minute = requests_per_minute
        self._insight_requests_per_minute = insight_requests_per_minute

    async def dispatch(self, request: Request, call_next) -> Response:
        caller = request.headers.get("X-Viewer-Id") or (request.client.host if request.client else "unknown")
        generating_insight = request.url.path == INSIGHTS_PATH and request.method == "POST"
        limit = (
            self._insight_requests_per_minute if generating_insight else self._requests_per_minute
        )
        # The two budgets need separate buckets. A token bucket is capped by the
        # limit it is handed, so billing both against one key per caller let a
        # single insight clamp that caller's general allowance to the insight
        # limit -- browsing turned into 429s after one insight.
        key = f"insight:{caller}" if generating_insight else caller
        decision = await self._rate_limiter.allow(key, limit)
        if not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited", "message": "too many requests",
                        "request_id": get_request_id() or "",
                    }
                },
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )
        return await call_next(request)
