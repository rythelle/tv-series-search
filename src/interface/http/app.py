import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import Settings
from infrastructure.observability.logging import configure_logging
from infrastructure.persistence.db import wait_for_database
from infrastructure.persistence.migration_runner import run_migrations
from infrastructure.resilience.token_bucket_rate_limiter import TokenBucketRateLimiter
from infrastructure.system_clock import SystemClock
from interface.http.container import Container
from interface.http.middleware.error_handler import register_error_handlers
from interface.http.middleware.rate_limit import RateLimitMiddleware
from interface.http.middleware.request_id import RequestIdMiddleware

FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        pool = await wait_for_database(
            connect=lambda: asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=10)
        )
        await run_migrations(pool)

        container = Container(settings, pool)
        app.state.container = container
        for router in container.build_routers():
            app.include_router(router, prefix=API_PREFIX)
        if FRONTEND_DIST.exists():
            app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

        outbox_task = asyncio.create_task(container.outbox_worker.run_forever())
        seed_task = asyncio.create_task(container.seed_popular_shows()) if settings.SEED_ON_START else None

        yield

        outbox_task.cancel()
        if seed_task is not None:
            seed_task.cancel()
        await pool.close()

    app = FastAPI(lifespan=lifespan)
    register_error_handlers(app)
    app.add_middleware(
        RateLimitMiddleware, rate_limiter=TokenBucketRateLimiter(SystemClock()),
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        insight_requests_per_minute=settings.INSIGHT_RATE_LIMIT_PER_MINUTE,
    )
    app.add_middleware(RequestIdMiddleware)

    return app
