import httpx
from fastapi import FastAPI

from interface.http.middleware.request_id import RequestIdMiddleware


def _app():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


async def test_generates_a_request_id_when_none_is_provided():
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ping")
    assert response.headers["X-Request-Id"]


async def test_echoes_a_provided_request_id():
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ping", headers={"X-Request-Id": "fixed-id"})
    assert response.headers["X-Request-Id"] == "fixed-id"
