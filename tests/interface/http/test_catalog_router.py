from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from application.errors import CatalogUnavailable
from application.use_cases.get_show_details import GetShowDetails
from application.use_cases.list_genres import ListGenres
from application.use_cases.list_popular_shows import ListPopularShows
from application.use_cases.search_shows import SearchShows
from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId
from interface.http.middleware.error_handler import register_error_handlers
from interface.http.routers.catalog import build_catalog_router
from tests.fakes.clock import FakeClock
from tests.fakes.show_fakes import FakeShowCatalog, FakeShowReadModelRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _show(show_id=1, name="Breaking Bad", genres=()):
    return Show(
        id=ShowId(show_id), name=name, premiered_year=2008, poster_url=None,
        summary="", genres=[Genre(g) for g in genres], rating=None, popularity=1.0,
        details_fetched_at=NOW, episodes_fetched_at=NOW,
    )


def _app(repo=None, catalog=None):
    repo = repo if repo is not None else FakeShowReadModelRepository(shows=[_show()])
    catalog = catalog if catalog is not None else FakeShowCatalog()
    search_shows = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))
    list_popular_shows = ListPopularShows(repository=repo)
    list_genres = ListGenres(repository=repo)
    get_show_details = GetShowDetails(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(
        build_catalog_router(
            search_shows, list_popular_shows, list_genres, get_show_details, search_result_limit=20
        )
    )
    return app


async def test_search_returns_items_and_the_degraded_flag():
    repo = FakeShowReadModelRepository()
    repo.search_results = [_show()]
    transport = httpx.ASGITransport(app=_app(repo=repo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/search", params={"q": "breaking"})

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["name"] == "Breaking Bad"
    assert body["degraded"] is False


async def test_popular_returns_items_from_the_read_model():
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/popular")

    assert response.status_code == 200
    assert response.json()["items"][0]["name"] == "Breaking Bad"


async def test_details_returns_seasons_grouped_by_number():
    repo = FakeShowReadModelRepository(
        shows=[_show()],
        episodes=[
            Episode(
                id=EpisodeId(10), show_id=ShowId(1), season=1, number=1, name="Pilot",
                airdate=None, runtime=None, summary="",
            )
        ],
    )
    transport = httpx.ASGITransport(app=_app(repo=repo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/1")

    assert response.status_code == 200
    body = response.json()
    assert body["seasons"][0]["episodes"][0]["name"] == "Pilot"


async def test_details_returns_404_for_an_unknown_show():
    transport = httpx.ASGITransport(
        app=_app(repo=FakeShowReadModelRepository(), catalog=FakeShowCatalog(raises=CatalogUnavailable("down")))
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/999")

    assert response.status_code == 404


async def test_genres_lists_the_genres_in_the_read_model():
    repo = FakeShowReadModelRepository(shows=[_show(1, genres=["Drama", "Crime"])])
    transport = httpx.ASGITransport(app=_app(repo=repo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/genres")

    assert response.status_code == 200
    assert sorted(response.json()["items"]) == ["Crime", "Drama"]


async def test_popular_narrows_the_listing_to_the_requested_genre():
    repo = FakeShowReadModelRepository(
        shows=[_show(1, genres=["Drama"]), _show(2, name="Arrested", genres=["Comedy"])]
    )
    transport = httpx.ASGITransport(app=_app(repo=repo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/popular", params={"genre": "Comedy"})

    assert [item["name"] for item in response.json()["items"]] == ["Arrested"]


async def test_search_forwards_the_genre_to_the_use_case():
    repo = FakeShowReadModelRepository()
    repo.search_results = [_show(1, genres=["Drama"]), _show(2, name="Arrested", genres=["Comedy"])]
    transport = httpx.ASGITransport(app=_app(repo=repo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/search", params={"q": "a", "genre": "Comedy"})

    assert [item["name"] for item in response.json()["items"]] == ["Arrested"]


async def test_search_ignores_a_blank_genre():
    repo = FakeShowReadModelRepository()
    repo.search_results = [_show(1, genres=["Drama"])]
    transport = httpx.ASGITransport(app=_app(repo=repo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/search", params={"q": "breaking", "genre": ""})

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["Breaking Bad"]


async def test_popular_pages_with_the_cursor_it_handed_out():
    repo = FakeShowReadModelRepository(shows=[
        _show(1, "Breaking Bad"), _show(2, "The Wire"), _show(3, "The Office"),
    ])
    transport = httpx.ASGITransport(app=_app(repo=repo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/shows/popular", params={"limit": 2})
        second = await client.get(
            "/shows/popular", params={"limit": 2, "cursor": first.json()["next_cursor"]}
        )

    assert first.status_code == 200
    assert [item["id"] for item in first.json()["items"]] == [1, 2]
    assert first.json()["total"] == 3
    assert [item["id"] for item in second.json()["items"]] == [3]


async def test_popular_offers_no_cursor_on_the_last_page():
    repo = FakeShowReadModelRepository(shows=[_show(1, "Breaking Bad")])
    transport = httpx.ASGITransport(app=_app(repo=repo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/popular", params={"limit": 20})

    assert response.json()["next_cursor"] is None


async def test_popular_reports_the_total_for_the_filtered_genre():
    repo = FakeShowReadModelRepository(shows=[
        _show(1, "Breaking Bad", genres=["Drama"]),
        _show(2, "The Office", genres=["Comedy"]),
    ])
    transport = httpx.ASGITransport(app=_app(repo=repo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/popular", params={"genre": "Comedy"})

    assert response.json()["total"] == 1


async def test_popular_rejects_a_cursor_it_never_issued():
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/shows/popular", params={"cursor": "not-a-position"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
