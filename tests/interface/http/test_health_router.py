import httpx
from fastapi import FastAPI

from interface.http.routers.health import build_health_router, build_ready_router


class _FakeConnection:
    async def fetchval(self, query: str):
        return 1

    async def __aenter__(self) -> "_FakeConnection":
        return self

    async def __aexit__(self, *args) -> None:
        return None


class _FakePool:
    def acquire(self):
        return _FakeConnection()


async def test_health_returns_ok_with_no_dependency_checks():
    app = FastAPI()
    app.include_router(build_health_router())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_returns_ready_when_the_pool_responds():
    app = FastAPI()
    app.include_router(build_ready_router(_FakePool()))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
