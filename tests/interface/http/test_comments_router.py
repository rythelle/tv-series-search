from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI

from application.use_cases.list_comments import ListComments
from application.use_cases.post_comment import PostComment
from interface.http.middleware.error_handler import register_error_handlers
from interface.http.routers.comments import build_comments_router
from tests.fakes.clock import FakeClock
from tests.fakes.comment_fakes import FakeCommentRepository, FakeEventPublisher, FakeUnitOfWork

VIEWER = "3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10"
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _app():
    comments = FakeCommentRepository()
    events = FakeEventPublisher()
    uow = FakeUnitOfWork(comments, events)
    clock = FakeClock(NOW)
    post_comment = PostComment(unit_of_work_factory=lambda: uow, clock=clock)
    list_comments = ListComments(repository=comments)

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(build_comments_router(post_comment, list_comments, page_size=50))
    return app, clock


async def _post(client, body="Great show!"):
    return await client.post(
        "/comments", json={"target_type": "show", "target_id": 1, "body": body},
        headers={"X-Viewer-Id": VIEWER},
    )


async def test_posting_a_comment_returns_201_with_the_created_comment():
    app, _clock = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await _post(client)

    assert response.status_code == 201
    assert response.json()["body"] == "Great show!"


async def test_posting_an_empty_comment_returns_400():
    app, _clock = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await _post(client, body="   ")

    assert response.status_code == 400


async def test_listing_comments_returns_newest_first():
    app, clock = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await _post(client, body="First")
        clock.set(NOW + timedelta(seconds=1))
        await _post(client, body="Second")

        response = await client.get("/comments", params={"target_type": "show", "target_id": 1})

    assert [c["body"] for c in response.json()["items"]] == ["Second", "First"]
