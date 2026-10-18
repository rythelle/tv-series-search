from application.errors import CatalogUnavailable
from application.use_cases.get_show_details import GetShowDetails
from config import Settings
from domain.entities.show import Show
from domain.value_objects.show_id import ShowId
from infrastructure.ai.heuristic_insight_generator import HeuristicInsightGenerator
from infrastructure.resilience.insight_decorators import CachedInsightGenerator, FallbackInsightGenerator
from interface.http.container import Container
from tests.fakes.show_fakes import FakeShowCatalog, FakeShowReadModelRepository


def test_wires_show_details_with_the_configured_stale_threshold():
    settings = Settings(AI_API_KEY="", SHOW_STALE_AFTER_SECONDS=123)
    container = Container(settings, pool=object())

    assert isinstance(container.get_show_details, GetShowDetails)
    assert container.get_show_details._stale_after_seconds == 123


def test_wires_a_heuristic_only_insight_chain_with_no_api_key():
    settings = Settings(AI_API_KEY="")
    container = Container(settings, pool=object())

    assert isinstance(container.insight_generator, CachedInsightGenerator)
    assert isinstance(container.insight_generator._inner, HeuristicInsightGenerator)


def test_wires_a_fallback_wrapped_chain_with_an_api_key():
    settings = Settings(AI_API_KEY="secret", AI_PROVIDER="huggingface")
    container = Container(settings, pool=object())

    assert isinstance(container.insight_generator._inner, FallbackInsightGenerator)


def test_builds_every_router():
    settings = Settings(AI_API_KEY="")
    container = Container(settings, pool=object())

    assert len(container.build_routers()) == 6


def _seeded_container(pages, seed_pages):
    settings = Settings(AI_API_KEY="", SEED_PAGES=seed_pages)
    container = Container(settings, pool=object())
    container.show_catalog = FakeShowCatalog(pages=pages)
    container.show_repository = FakeShowReadModelRepository()
    return container


def _show(show_id):
    return Show(
        id=ShowId(show_id), name=f"Show {show_id}", premiered_year=2020, poster_url=None,
        summary="", genres=[], rating=None, popularity=1.0,
        details_fetched_at=None, episodes_fetched_at=None,
    )


async def test_seed_fills_the_catalog_from_the_paginated_index():
    container = _seeded_container(pages=[[_show(1), _show(2)], [_show(3)]], seed_pages=2)

    await container.seed_popular_shows()

    assert sorted(container.show_repository.shows) == [1, 2, 3]
    assert container.show_catalog.page_calls == [0, 1]


async def test_seed_stops_once_the_index_runs_out_of_pages():
    container = _seeded_container(pages=[[_show(1)]], seed_pages=4)

    await container.seed_popular_shows()

    assert sorted(container.show_repository.shows) == [1]
    assert container.show_catalog.page_calls == [0, 1]


async def test_seed_starts_at_page_zero_because_the_index_is_zero_based():
    # /shows?page=0 is the first page (ids 1-249); starting at 1 silently skips it.
    container = _seeded_container(pages=[[_show(1)], [_show(2)]], seed_pages=1)

    await container.seed_popular_shows()

    assert container.show_catalog.page_calls == [0]
    assert sorted(container.show_repository.shows) == [1]


async def test_seed_stamps_the_fetch_time_so_search_does_not_treat_rows_as_stale():
    container = _seeded_container(pages=[[_show(1)]], seed_pages=1)

    await container.seed_popular_shows()

    assert container.show_repository.shows[1].details_fetched_at is not None


async def test_seed_survives_the_catalog_being_unavailable():
    container = _seeded_container(pages=[], seed_pages=2)
    container.show_catalog.raises = CatalogUnavailable("tvmaze down")

    await container.seed_popular_shows()

    assert container.show_repository.shows == {}
