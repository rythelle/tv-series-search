from datetime import datetime, timezone

import pytest

from application.dto.show_dto import PopularCursor
from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId
from infrastructure.persistence.postgres_show_read_model_repository import (
    PostgresShowReadModelRepository,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _show(show_id, name, popularity=1.0, genres=None):
    return Show(
        id=ShowId(show_id), name=name, premiered_year=2008, poster_url=None,
        summary="A show.", genres=[Genre(g) for g in (genres or [])], rating=9.0,
        popularity=popularity, details_fetched_at=NOW, episodes_fetched_at=NOW,
    )


async def test_upsert_then_get_show_round_trips(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Breaking Bad", genres=["Drama"])])

    show = await repo.get_show(ShowId(1))

    assert show.name == "Breaking Bad"
    assert [g.value for g in show.genres] == ["Drama"]


async def test_upsert_is_idempotent_and_updates_existing_rows(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Breaking Bad")])
    await repo.upsert_shows([_show(1, "Breaking Bad (Remastered)")])

    show = await repo.get_show(ShowId(1))
    assert show.name == "Breaking Bad (Remastered)"


async def test_search_matches_an_exact_substring(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Breaking Bad"), _show(2, "Better Call Saul")])

    results = await repo.search("Breaking", limit=10)

    assert [s.id.value for s in results] == [1]


async def test_search_is_typo_tolerant_via_trigram_similarity(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Casarão")])

    results = await repo.search("casa", limit=10)

    assert [s.id.value for s in results] == [1]


async def test_search_returns_nothing_for_an_unrelated_query(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Breaking Bad")])

    assert await repo.search("zzzzzzzz", limit=10) == []


async def test_list_popular_orders_by_popularity_descending(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Low", popularity=1.0), _show(2, "High", popularity=99.0)])

    results = await repo.list_popular(limit=2)

    assert [s.id.value for s in results] == [2, 1]


async def test_upsert_and_get_episodes_round_trip(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Breaking Bad")])
    episode = Episode(
        id=EpisodeId(10), show_id=ShowId(1), season=1, number=1, name="Pilot",
        airdate="2008-01-20", runtime=58, summary="",
    )
    await repo.upsert_episodes(ShowId(1), [episode])

    episodes = await repo.get_episodes(ShowId(1))
    single = await repo.get_episode(EpisodeId(10))

    assert [e.id for e in episodes] == [EpisodeId(10)]
    assert single.name == "Pilot"


async def test_get_show_returns_none_for_an_unknown_id(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    assert await repo.get_show(ShowId(999)) is None


async def test_get_episode_returns_none_for_an_unknown_id(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    assert await repo.get_episode(EpisodeId(999)) is None


async def test_search_narrows_results_to_the_requested_genre(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([
        _show(1, "Breaking Bad", genres=["Drama", "Crime"]),
        _show(2, "Breaking In", genres=["Comedy"]),
    ])

    results = await repo.search("breaking", limit=10, genre=Genre("Comedy"))

    assert [s.id.value for s in results] == [2]


async def test_search_without_a_genre_keeps_every_match(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([
        _show(1, "Breaking Bad", genres=["Drama"]),
        _show(2, "Breaking In", genres=["Comedy"]),
    ])

    results = await repo.search("breaking", limit=10)

    assert len(results) == 2


async def test_list_popular_narrows_results_to_the_requested_genre(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([
        _show(1, "Breaking Bad", popularity=99.0, genres=["Drama"]),
        _show(2, "Arrested Development", popularity=10.0, genres=["Comedy"]),
        _show(3, "The Office", popularity=50.0, genres=["Comedy"]),
    ])

    results = await repo.list_popular(limit=10, genre=Genre("Comedy"))

    assert [s.id.value for s in results] == [3, 2]


async def test_list_genres_returns_distinct_genres_ordered_by_show_count(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([
        _show(1, "Breaking Bad", genres=["Drama", "Crime"]),
        _show(2, "The Wire", genres=["Drama", "Crime"]),
        _show(3, "The Office", genres=["Comedy"]),
    ])

    genres = await repo.list_genres()

    assert [g.value for g in genres] == ["Crime", "Drama", "Comedy"]


async def test_list_genres_is_empty_when_no_show_has_a_genre(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Breaking Bad")])

    assert await repo.list_genres() == []


async def test_search_matches_a_genre_whatever_casing_the_caller_used(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Breaking Bad", genres=["Science-Fiction"])])

    results = await repo.search("breaking", limit=10, genre=Genre("science-fiction"))

    assert [s.id.value for s in results] == [1]


async def test_list_popular_matches_a_genre_whatever_casing_the_caller_used(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "The Office", genres=["Comedy"])])

    results = await repo.list_popular(limit=10, genre=Genre("COMEDY"))

    assert [s.id.value for s in results] == [1]


async def test_list_genres_collapses_spellings_of_the_same_genre(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "A", genres=["Comedy"]), _show(2, "B", genres=["comedy"])])

    genres = await repo.list_genres()

    # Which spelling wins is the collation's call; what matters is that the
    # dropdown gets one entry, not two that filter identically.
    assert genres == [Genre("Comedy")]


async def test_the_genre_filter_uses_the_normalized_gin_index(clean_pool):
    # The whole point of storing the normalized form is that the filter stays
    # indexable; seq_scan is disabled so the plan has to prove the index applies.
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "The Office", genres=["Comedy"])])

    async with clean_pool.acquire() as conn:
        await conn.execute("SET enable_seqscan = off")
        rows = await conn.fetch(
            "EXPLAIN SELECT id FROM shows WHERE genres_normalized && ARRAY['comedy']::text[]"
        )

    assert "shows_genres_normalized_idx" in "\n".join(row["QUERY PLAN"] for row in rows)


async def test_list_popular_resumes_after_the_cursor(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([
        _show(1, "Third", popularity=10.0),
        _show(2, "First", popularity=99.0),
        _show(3, "Second", popularity=50.0),
    ])

    results = await repo.list_popular(limit=2, after=PopularCursor(popularity=99.0, show_id=2))

    assert [s.id.value for s in results] == [3, 1]


async def test_list_popular_pages_do_not_overlap_when_popularity_ties(clean_pool):
    # TVMaze weights are small integers, so ties are the common case. Without a
    # tiebreaker the planner may order tied rows differently per query and the
    # same show would show up on two pages (or on none) as the user scrolls.
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(show_id, f"Tied {show_id}", popularity=7.0) for show_id in range(1, 8)])

    seen = []
    cursor = None
    for _ in range(3):
        page = await repo.list_popular(limit=3, after=cursor)
        seen.extend(s.id.value for s in page)
        cursor = PopularCursor(popularity=page[-1].popularity, show_id=page[-1].id.value)

    assert seen == sorted(set(seen))
    assert len(seen) == 7


async def test_list_popular_keeps_its_place_when_a_row_lands_above_the_cursor(clean_pool):
    # The payoff of the keyset: the listing deepens the catalog while a reader is
    # scrolling, so rows appear above them mid-scroll. Under OFFSET each one
    # pushed the rest down and the next page repeated a show.
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([
        _show(1, "First", popularity=90.0),
        _show(2, "Second", popularity=80.0),
        _show(3, "Third", popularity=70.0),
    ])

    first = await repo.list_popular(limit=2)
    await repo.upsert_shows([_show(99, "Arrived mid-scroll", popularity=100.0)])
    second = await repo.list_popular(
        limit=2, after=PopularCursor(popularity=first[-1].popularity, show_id=first[-1].id.value)
    )

    assert [s.id.value for s in first] == [1, 2]
    assert [s.id.value for s in second] == [3]


async def test_list_popular_applies_the_cursor_within_a_genre(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([
        _show(1, "Breaking Bad", popularity=99.0, genres=["Drama"]),
        _show(2, "Arrested Development", popularity=10.0, genres=["Comedy"]),
        _show(3, "The Office", popularity=50.0, genres=["Comedy"]),
    ])

    results = await repo.list_popular(
        limit=10, after=PopularCursor(popularity=50.0, show_id=3), genre=Genre("Comedy")
    )

    assert [s.id.value for s in results] == [2]


async def test_list_popular_reads_the_ranking_through_its_index(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(i, f"Show {i}", popularity=float(i)) for i in range(1, 40)])

    async with clean_pool.acquire() as conn:
        await conn.execute("SET enable_seqscan = off")
        rows = await conn.fetch(
            "EXPLAIN SELECT id FROM shows WHERE popularity < 20 ORDER BY popularity DESC, id LIMIT 5"
        )

    assert "shows_popularity_id_idx" in "\n".join(row["QUERY PLAN"] for row in rows)


async def test_count_popular_counts_every_row_matching_the_genre(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([
        _show(1, "Breaking Bad", genres=["Drama"]),
        _show(2, "Arrested Development", genres=["Comedy"]),
        _show(3, "The Office", genres=["Comedy"]),
    ])

    assert await repo.count_popular() == 3
    assert await repo.count_popular(genre=Genre("Comedy")) == 2


async def test_search_finds_the_query_inside_a_long_title(clean_pool):
    # similarity() compares the whole string, so every word the query does not
    # mention dilutes the score: "dext" rated "DEA" (0.29) above "Dexter: New
    # Blood" (0.22) and the threshold kept the wrong one.
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Dexter: New Blood"), _show(2, "DEA")])

    results = await repo.search("dext", limit=10)

    assert [s.id.value for s in results] == [1]


async def test_search_ranks_the_closest_title_first(clean_pool):
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([
        _show(1, "Dex Hamilton: Alien Entomologist"),
        _show(2, "Dexter"),
    ])

    results = await repo.search("dext", limit=10)

    assert [s.id.value for s in results] == [2, 1]


async def test_search_applies_the_configured_word_similarity_threshold(clean_pool):
    strict = PostgresShowReadModelRepository(clean_pool, word_similarity_threshold=0.9)
    loose = PostgresShowReadModelRepository(clean_pool, word_similarity_threshold=0.3)
    await strict.upsert_shows([_show(1, "DEA")])

    # Same pool, same connections: the threshold is set per transaction, so a
    # strict search must not leave its setting behind for the next caller.
    assert await strict.search("dext", limit=10) == []
    assert [s.id.value for s in await loose.search("dext", limit=10)] == [1]


async def test_the_name_match_uses_the_trigram_gin_index(clean_pool):
    # word_similarity() spelled as a function call cannot use an index -- it is a
    # seq scan that rescores every row (4.1s against 2k rows, measured, versus
    # 18ms). Only the %> operator reads shows_name_trgm_idx, which is why the
    # threshold travels as a GUC instead of a query parameter.
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Dexter: New Blood")])

    async with clean_pool.acquire() as conn:
        await conn.execute("SET enable_seqscan = off")
        rows = await conn.fetch("EXPLAIN SELECT id FROM shows WHERE name %> 'dext'")

    assert "shows_name_trgm_idx" in "\n".join(row["QUERY PLAN"] for row in rows)


async def test_search_still_tolerates_a_transposed_typo_at_the_default_threshold(clean_pool):
    # "brekaing bad" scores exactly 0.50 against "Breaking Bad" -- the default
    # threshold's own value, admitted because %> compares >=. The documented
    # typo example therefore still works, but with zero headroom: nudging
    # TRIGRAM_WORD_SIMILARITY_THRESHOLD up at all drops it.
    repo = PostgresShowReadModelRepository(clean_pool)
    await repo.upsert_shows([_show(1, "Breaking Bad")])

    results = await repo.search("brekaing bad", limit=10)

    assert [s.id.value for s in results] == [1]
