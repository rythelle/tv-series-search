import asyncpg
from fastapi import APIRouter


def build_health_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    return router


def build_ready_router(pool: asyncpg.Pool) -> APIRouter:
    router = APIRouter()

    @router.get("/ready")
    async def ready():
        async with pool.acquire() as connection:
            await connection.fetchval("SELECT 1")
        return {"status": "ready"}

    return router
