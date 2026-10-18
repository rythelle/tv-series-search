from datetime import datetime, timezone

from application.dto.show_dto import ListPopularShowsInput, PopularCursor
from application.use_cases.list_popular_shows import ListPopularShows
from domain.entities.show import Show
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId
from tests.fakes.show_fakes import FakeShowReadModelRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _show(show_id, popularity, genres=()):
    return Show(
        id=ShowId(show_id), name=f"Show {show_id}", premiered_year=2020, poster_url=None,
        summary="", genres=[Genre(g) for g in genres], rating=None, popularity=popularity,
        details_fetched_at=NOW, episodes_fetched_at=NOW,
    )


async def test_returns_shows_ordered_by_popularity_within_the_limit():
    repo = FakeShowReadModelRepository(shows=[_show(1, 10.0), _show(2, 50.0), _show(3, 30.0)])

    result = await ListPopularShows(repository=repo).execute(ListPopularShowsInput(limit=2))

    assert [s.id.value for s in result.items] == [2, 3]


async def test_filters_popular_shows_by_genre():
    repo = FakeShowReadModelRepository(shows=[_show(1, 10.0), _show(4, 99.0, genres=["Comedy"])])

    result = await ListPopularShows(repository=repo).execute(
        ListPopularShowsInput(limit=10, genre="Comedy")
    )

    assert [s.id.value for s in result.items] == [4]


async def test_returns_the_rows_after_the_cursor():
    repo = FakeShowReadModelRepository(shows=[_show(1, 10.0), _show(2, 50.0), _show(3, 30.0)])

    result = await ListPopularShows(repository=repo).execute(
        ListPopularShowsInput(limit=2, cursor=PopularCursor(popularity=30.0, show_id=3))
    )

    assert [s.id.value for s in result.items] == [1]


async def test_walks_past_a_popularity_tie_without_repeating_a_show():
    repo = FakeShowReadModelRepository(shows=[_show(i, 7.0) for i in (1, 2, 3, 4)])
    use_case = ListPopularShows(repository=repo)

    first = await use_case.execute(ListPopularShowsInput(limit=2))
    second = await use_case.execute(ListPopularShowsInput(limit=2, cursor=first.next_cursor))

    assert [s.id.value for s in first.items] == [1, 2]
    assert [s.id.value for s in second.items] == [3, 4]


async def test_a_show_arriving_mid_scroll_does_not_shift_the_next_page():
    # Why the listing is keyset and not offset: a search upserts every hit it
    # gets back, so rows appear in the middle of the ranking while someone is
    # browsing. Under OFFSET a row landing above the reader pushes the rest down
    # and the next page repeats a show.
    repo = FakeShowReadModelRepository(shows=[_show(1, 90.0), _show(2, 80.0), _show(3, 70.0)])
    use_case = ListPopularShows(repository=repo)

    first = await use_case.execute(ListPopularShowsInput(limit=2))
    await repo.upsert_shows([_show(99, 100.0)])
    second = await use_case.execute(ListPopularShowsInput(limit=2, cursor=first.next_cursor))

    assert [s.id.value for s in first.items] == [1, 2]
    assert [s.id.value for s in second.items] == [3]


async def test_reports_the_total_so_the_caller_can_show_a_count():
    repo = FakeShowReadModelRepository(shows=[_show(1, 10.0), _show(2, 50.0), _show(3, 30.0)])

    result = await ListPopularShows(repository=repo).execute(ListPopularShowsInput(limit=2))

    assert result.total == 3


async def test_the_total_counts_only_the_filtered_genre():
    repo = FakeShowReadModelRepository(shows=[_show(1, 10.0), _show(4, 99.0, genres=["Comedy"])])

    result = await ListPopularShows(repository=repo).execute(
        ListPopularShowsInput(limit=10, genre="Comedy")
    )

    assert result.total == 1


async def test_offers_no_cursor_on_the_last_page():
    repo = FakeShowReadModelRepository(shows=[_show(1, 10.0), _show(2, 50.0)])

    result = await ListPopularShows(repository=repo).execute(ListPopularShowsInput(limit=10))

    assert result.next_cursor is None


async def test_offers_no_cursor_for_an_empty_listing():
    result = await ListPopularShows(repository=FakeShowReadModelRepository()).execute(
        ListPopularShowsInput(limit=10)
    )

    assert result.items == []
    assert result.next_cursor is None


def test_a_cursor_survives_a_round_trip_through_its_encoded_form():
    cursor = PopularCursor(popularity=70.0, show_id=161)

    assert PopularCursor.parse(cursor.encode()) == cursor


def test_a_malformed_cursor_is_rejected():
    for raw in ("", "abc", "70.0", "70.0:", ":161", "70.0:abc"):
        try:
            PopularCursor.parse(raw)
        except ValueError:
            continue
        raise AssertionError(f"{raw!r} should not parse")
