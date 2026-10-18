from datetime import datetime, timedelta, timezone

import pytest

from application.dto.show_dto import GetShowDetailsInput
from application.errors import CatalogUnavailable
from application.use_cases.get_show_details import GetShowDetails
from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.errors import ShowNotFound
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId
from tests.fakes.clock import FakeClock
from tests.fakes.show_fakes import FakeShowCatalog, FakeShowReadModelRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _show(show_id=1, fetched_at=NOW):
    return Show(
        id=ShowId(show_id), name="Breaking Bad", premiered_year=2008, poster_url=None,
        summary="", genres=[], rating=None, popularity=1.0,
        details_fetched_at=fetched_at, episodes_fetched_at=fetched_at,
    )


def _episode(episode_id, show_id=1, season=1, number=1):
    return Episode(
        id=EpisodeId(episode_id), show_id=ShowId(show_id), season=season, number=number,
        name="Pilot", airdate=None, runtime=None, summary="",
    )


async def test_returns_fresh_local_show_grouped_by_season():
    repo = FakeShowReadModelRepository(shows=[_show()], episodes=[_episode(10)])
    use_case = GetShowDetails(repository=repo, catalog=FakeShowCatalog(), clock=FakeClock(NOW))

    result = await use_case.execute(GetShowDetailsInput(show_id=1))

    assert result.show.id == ShowId(1)
    assert [s.number for s in result.seasons] == [1]
    assert result.degraded is False


async def test_fetches_episodes_for_a_show_cached_by_search_without_episodes():
    cached = _show()
    cached.episodes_fetched_at = None
    repo = FakeShowReadModelRepository(shows=[cached])
    catalog = FakeShowCatalog(show=_show(), episodes=[_episode(10)])
    use_case = GetShowDetails(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(GetShowDetailsInput(show_id=1))

    assert [season.number for season in result.seasons] == [1]
    assert repo.shows[1].episodes_fetched_at == NOW


async def test_fetches_from_catalog_in_parallel_when_missing_locally():
    repo = FakeShowReadModelRepository()
    catalog = FakeShowCatalog(show=_show(), episodes=[_episode(10)])
    use_case = GetShowDetails(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(GetShowDetailsInput(show_id=1))

    assert result.show.id == ShowId(1)
    assert repo.shows[1].id == ShowId(1)
    assert repo.episodes[10].id == EpisodeId(10)
    assert result.degraded is False


async def test_refetches_when_stale_even_if_present_locally():
    stale_at = NOW - timedelta(days=2)
    repo = FakeShowReadModelRepository(shows=[_show(fetched_at=stale_at)], episodes=[_episode(10)])
    catalog = FakeShowCatalog(show=_show(), episodes=[_episode(10)])
    use_case = GetShowDetails(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(GetShowDetailsInput(show_id=1))

    assert result.degraded is False
    assert repo.shows[1].details_fetched_at == NOW


async def test_serves_stale_local_data_as_degraded_when_catalog_fails():
    stale_at = NOW - timedelta(days=2)
    repo = FakeShowReadModelRepository(shows=[_show(fetched_at=stale_at)], episodes=[_episode(10)])
    catalog = FakeShowCatalog(raises=CatalogUnavailable("timeout"))
    use_case = GetShowDetails(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(GetShowDetailsInput(show_id=1))

    assert result.degraded is True
    assert result.show.id == ShowId(1)


async def test_raises_show_not_found_when_missing_everywhere():
    repo = FakeShowReadModelRepository()
    catalog = FakeShowCatalog(raises=CatalogUnavailable("timeout"))
    use_case = GetShowDetails(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    with pytest.raises(ShowNotFound):
        await use_case.execute(GetShowDetailsInput(show_id=999))


async def test_stamps_a_fetch_time_on_a_show_the_catalog_returns_unstamped():
    # The real TVMazeShowCatalog mapper never sets details_fetched_at/episodes_fetched_at
    # — the use case must stamp "now" before persisting, or every later call would see
    # None, judge the row permanently stale, and refetch from TVMaze forever.
    repo = FakeShowReadModelRepository()
    catalog = FakeShowCatalog(show=_show(fetched_at=None), episodes=[_episode(10)])
    use_case = GetShowDetails(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(GetShowDetailsInput(show_id=1))

    assert result.show.details_fetched_at == NOW
    assert result.show.episodes_fetched_at == NOW
    assert repo.shows[1].details_fetched_at == NOW
