from datetime import datetime, timedelta, timezone

from application.dto.show_dto import SearchShowsInput
from application.errors import CatalogUnavailable
from application.use_cases.search_shows import SearchShows
from domain.entities.show import Show
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId
from tests.fakes.clock import FakeClock
from tests.fakes.show_fakes import FakeShowCatalog, FakeShowReadModelRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _show(show_id, name="Breaking Bad", fetched_at=NOW, genres=()):
    return Show(
        id=ShowId(show_id), name=name, premiered_year=2008, poster_url=None,
        summary="", genres=[Genre(g) for g in genres], rating=None, popularity=1.0,
        details_fetched_at=fetched_at, episodes_fetched_at=fetched_at,
    )


async def test_merges_local_and_catalog_hits_without_duplicates():
    # The read model holds a slice of the catalog, so a local hit is no evidence
    # the catalog has nothing more. Searching "dex" matched the one stored Dexter
    # and answered a single result while TVMaze also had Dino Dex and
    # Dex Hamilton; the catalog has to be consulted and the two merged.
    repo = FakeShowReadModelRepository()
    repo.search_results = [_show(1, name="Dexter")]
    catalog = FakeShowCatalog(
        search_results=[
            _show(2, name="Dino Dex"),
            _show(1, name="Dexter"),
            _show(3, name="Dex Hamilton"),
        ]
    )
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(SearchShowsInput(query="dex", limit=20))

    assert [s.name for s in result.items] == ["Dexter", "Dino Dex", "Dex Hamilton"]
    assert result.degraded is False


async def test_asks_the_catalog_even_when_the_local_hits_are_fresh():
    # Freshness says the stored copy of a row is current, never that the stored
    # set is complete -- the old short-circuit confused the two.
    repo = FakeShowReadModelRepository()
    repo.search_results = [_show(1)]
    catalog = FakeShowCatalog()
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    await use_case.execute(SearchShowsInput(query="breaking", limit=20))

    assert catalog.search_calls == ["breaking"]


async def test_answers_the_same_hits_however_often_the_query_is_repeated():
    # The background refresh made the first search answer from the read model and
    # the second from the warmed cache, so the same query gave different results.
    repo = FakeShowReadModelRepository()
    repo.search_results = [_show(1, name="Dexter")]
    catalog = FakeShowCatalog(search_results=[_show(2, name="Dino Dex")])
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    first = await use_case.execute(SearchShowsInput(query="dex", limit=20))
    second = await use_case.execute(SearchShowsInput(query="dex", limit=20))

    assert [s.id.value for s in first.items] == [s.id.value for s in second.items]


async def test_prefers_the_catalog_copy_of_a_show_the_read_model_also_holds():
    repo = FakeShowReadModelRepository()
    stale_at = NOW - timedelta(days=2)
    repo.search_results = [_show(1, fetched_at=stale_at)]
    catalog = FakeShowCatalog(search_results=[_show(1, name="Breaking Bad (refreshed)")])
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(SearchShowsInput(query="breaking", limit=20))

    assert result.items[0].name == "Breaking Bad (refreshed)"
    assert result.degraded is False
    assert repo.shows[1].name == "Breaking Bad (refreshed)"


async def test_caps_the_merged_hits_at_the_requested_limit():
    repo = FakeShowReadModelRepository()
    repo.search_results = [_show(1, name="Dexter")]
    catalog = FakeShowCatalog(
        search_results=[_show(2, name="Dino Dex"), _show(3, name="Dex Hamilton")]
    )
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(SearchShowsInput(query="dex", limit=2))

    assert [s.name for s in result.items] == ["Dexter", "Dino Dex"]


async def test_finds_shows_the_read_model_does_not_hold_at_all():
    repo = FakeShowReadModelRepository()
    catalog = FakeShowCatalog(search_results=[_show(2, name="Casarão")])
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(SearchShowsInput(query="casa", limit=20))

    assert result.items[0].name == "Casarão"
    assert result.degraded is False


async def test_stamps_a_fetch_time_on_shows_the_catalog_returns_unstamped():
    # The real TVMazeShowCatalog mapper never sets details_fetched_at — it is the
    # use case's job to stamp "now" before persisting, or the next call would see
    # details_fetched_at=None, judge the row permanently stale, and refetch forever.
    repo = FakeShowReadModelRepository()
    catalog = FakeShowCatalog(search_results=[_show(2, name="Casarão", fetched_at=None)])
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(SearchShowsInput(query="casa", limit=20))

    assert result.items[0].details_fetched_at == NOW
    assert repo.shows[2].details_fetched_at == NOW


async def test_returns_degraded_empty_when_catalog_fails_and_nothing_local():
    repo = FakeShowReadModelRepository()
    catalog = FakeShowCatalog(raises=CatalogUnavailable("timeout"))
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(SearchShowsInput(query="casa", limit=20))

    assert result.items == []
    assert result.degraded is True


async def test_returns_local_hits_as_degraded_when_the_catalog_fails():
    # Answering what is stored beats answering nothing, but the client is told the
    # set may be short so it can say so.
    repo = FakeShowReadModelRepository()
    repo.search_results = [_show(1)]
    catalog = FakeShowCatalog(raises=CatalogUnavailable("timeout"))
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(SearchShowsInput(query="breaking", limit=20))

    assert len(result.items) == 1
    assert result.degraded is True


async def test_narrows_local_hits_to_the_requested_genre():
    repo = FakeShowReadModelRepository()
    use_case = SearchShows(repository=repo, catalog=FakeShowCatalog(), clock=FakeClock(NOW))

    await use_case.execute(SearchShowsInput(query="bad", limit=20, genre="Drama"))

    assert repo.search_calls == [("bad", 20, Genre("Drama"))]


async def test_drops_catalog_hits_outside_the_requested_genre():
    repo = FakeShowReadModelRepository()
    catalog = FakeShowCatalog(
        search_results=[
            _show(1, name="Breaking Bad", genres=["Drama"]),
            _show(2, name="Breaking In", genres=["Comedy"]),
        ]
    )
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(SearchShowsInput(query="breaking", limit=20, genre="Drama"))

    assert [s.id.value for s in result.items] == [1]


async def test_still_caches_every_catalog_hit_even_when_filtering_by_genre():
    # The genre filter is a view over the response; throwing away the other hits
    # would make the read model miss rows a different genre filter needs later.
    repo = FakeShowReadModelRepository()
    catalog = FakeShowCatalog(
        search_results=[
            _show(1, name="Breaking Bad", genres=["Drama"]),
            _show(2, name="Breaking In", genres=["Comedy"]),
        ]
    )
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    await use_case.execute(SearchShowsInput(query="breaking", limit=20, genre="Drama"))

    assert sorted(repo.shows) == [1, 2]


async def test_matches_catalog_hits_whatever_casing_the_request_used():
    # The dropdown sends the catalog's own spelling, but a hand-written
    # ?genre=drama must not come back empty.
    repo = FakeShowReadModelRepository()
    catalog = FakeShowCatalog(search_results=[_show(1, name="Breaking Bad", genres=["Drama"])])
    use_case = SearchShows(repository=repo, catalog=catalog, clock=FakeClock(NOW))

    result = await use_case.execute(SearchShowsInput(query="breaking", limit=20, genre="drama"))

    assert [s.id.value for s in result.items] == [1]
