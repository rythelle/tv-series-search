from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from application.use_cases.list_watched_episodes import ListWatchedEpisodes
from application.use_cases.toggle_episode_watched import ToggleEpisodeWatched
from domain.entities.episode import Episode
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId
from interface.http.middleware.error_handler import register_error_handlers
from interface.http.routers.watched import build_watched_router
from tests.fakes.clock import FakeClock
from tests.fakes.show_fakes import FakeShowReadModelRepository
from tests.fakes.watch_fakes import FakeWatchRepository

VIEWER = "3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10"
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _episode(episode_id=10):
    return Episode(
        id=EpisodeId(episode_id), show_id=ShowId(1), season=1, number=1, name="Pilot",
        airdate=None, runtime=None, summary="",
    )


def _app():
    show_repo = FakeShowReadModelRepository(episodes=[_episode()])
    watch_repo = FakeWatchRepository()
    list_watched_episodes = ListWatchedEpisodes(repository=watch_repo)
    toggle_episode_watched = ToggleEpisodeWatched(
        watch_repository=watch_repo, show_repository=show_repo, clock=FakeClock(NOW),
    )
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(build_watched_router(list_watched_episodes, toggle_episode_watched))
    return app, watch_repo


async def test_marking_then_listing_returns_the_episode():
    app, _watch_repo = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        mark_response = await client.put("/viewers/me/watched/10", headers={"X-Viewer-Id": VIEWER})
        list_response = await client.get(
            "/viewers/me/watched", params={"show_id": 1}, headers={"X-Viewer-Id": VIEWER},
        )

    assert mark_response.status_code == 204
    assert list_response.json() == {"episode_ids": [10]}


async def test_unmarking_removes_the_episode():
    app, _watch_repo = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.put("/viewers/me/watched/10", headers={"X-Viewer-Id": VIEWER})
        unmark_response = await client.delete("/viewers/me/watched/10", headers={"X-Viewer-Id": VIEWER})
        list_response = await client.get(
            "/viewers/me/watched", params={"show_id": 1}, headers={"X-Viewer-Id": VIEWER},
        )

    assert unmark_response.status_code == 204
    assert list_response.json() == {"episode_ids": []}


async def test_marking_an_unknown_episode_returns_404():
    app, _watch_repo = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/viewers/me/watched/999", headers={"X-Viewer-Id": VIEWER})

    assert response.status_code == 404


async def test_a_missing_viewer_header_is_rejected():
    app, _watch_repo = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/viewers/me/watched/10")

    assert response.status_code == 422


async def test_a_malformed_viewer_header_returns_400():
    app, _watch_repo = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/viewers/me/watched/10", headers={"X-Viewer-Id": "not-a-uuid"})

    assert response.status_code == 400
