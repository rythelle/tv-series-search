from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from application.insight_cache_key import build_insight_cache_key
from application.use_cases.generate_insight import GenerateInsight
from application.use_cases.get_cached_insight import GetCachedInsight
from domain.entities.insight import Insight
from domain.entities.show import Show
from domain.value_objects.genre import Genre
from domain.value_objects.insight_text import InsightText
from domain.value_objects.show_id import ShowId
from interface.http.middleware.error_handler import register_error_handlers
from interface.http.routers.insights import build_insights_router
from tests.fakes.comment_fakes import FakeCommentRepository
from tests.fakes.insight_fakes import FakeInsightCache, FakeInsightGenerator
from tests.fakes.show_fakes import FakeShowReadModelRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _show():
    return Show(
        id=ShowId(1), name="Breaking Bad", premiered_year=2008, poster_url=None,
        summary="A show.", genres=[Genre("Drama")], rating=None, popularity=1.0,
        details_fetched_at=NOW, episodes_fetched_at=NOW,
    )


def _app(insight=None, cache=None):
    show_repo = FakeShowReadModelRepository(shows=[_show()])
    comment_repo = FakeCommentRepository()
    generator = FakeInsightGenerator(
        insight or Insight(text=InsightText("A tense drama."), source="llm", model="hf", generated_at=NOW)
    )
    generate_insight = GenerateInsight(
        show_repository=show_repo, comment_repository=comment_repo, insight_generator=generator,
    )
    get_cached_insight = GetCachedInsight(
        show_repository=show_repo, comment_repository=comment_repo, cache=cache or FakeInsightCache(),
    )
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(build_insights_router(generate_insight, get_cached_insight))
    return app


async def test_generates_an_insight_without_exposing_its_provenance():
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/insights", json={"target_type": "show", "target_id": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "A tense drama."
    assert "source" not in body
    assert "model" not in body


async def test_returns_404_for_an_unknown_show():
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/insights", json={"target_type": "show", "target_id": 999})

    assert response.status_code == 404


async def test_peek_returns_204_when_no_insight_is_cached():
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/insights", params={"target_type": "show", "target_id": 1})

    assert response.status_code == 204


async def test_peek_returns_the_cached_insight_without_its_provenance():
    cache = FakeInsightCache()
    key = build_insight_cache_key("show", 1, ["Drama"], "A show.", 0, 0)
    await cache.set(
        key, "show", 1,
        Insight(text=InsightText("Cached take."), source="fallback", model=None, generated_at=NOW),
        NOW,
    )
    transport = httpx.ASGITransport(app=_app(cache=cache))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/insights", params={"target_type": "show", "target_id": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "Cached take."
    assert "source" not in body
    assert "model" not in body
