from datetime import datetime, timezone

import pytest

from application.dto.insight_dto import GenerateInsightInput
from application.insight_cache_key import build_insight_cache_key
from application.use_cases.get_cached_insight import GetCachedInsight
from domain.entities.episode import Episode
from domain.entities.insight import Insight
from domain.entities.show import Show
from domain.errors import EpisodeNotFound, ShowNotFound
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.insight_text import InsightText
from domain.value_objects.show_id import ShowId
from tests.fakes.comment_fakes import FakeCommentRepository
from tests.fakes.insight_fakes import FakeInsightCache
from tests.fakes.show_fakes import FakeShowReadModelRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _show():
    return Show(
        id=ShowId(1), name="Breaking Bad", premiered_year=2008, poster_url=None,
        summary="A chemistry teacher.", genres=[Genre("Drama"), Genre("Crime")], rating=None,
        popularity=1.0, details_fetched_at=NOW, episodes_fetched_at=NOW,
    )


def _episode():
    return Episode(
        id=EpisodeId(42), show_id=ShowId(1), season=1, number=1, name="Pilot",
        airdate="2008-01-20", runtime=58, summary="A teacher cooks.",
    )


def _insight(text="A tense drama."):
    return Insight(text=InsightText(text), source="llm", model="hf", generated_at=NOW)


def _use_case(show_repo=None, comment_repo=None, cache=None):
    show_repo = show_repo or FakeShowReadModelRepository(shows=[_show()])
    comment_repo = comment_repo or FakeCommentRepository()
    cache = cache or FakeInsightCache()
    return GetCachedInsight(
        show_repository=show_repo, comment_repository=comment_repo, cache=cache,
    ), cache


async def test_returns_none_when_nothing_is_cached():
    use_case, _cache = _use_case()

    result = await use_case.execute(GenerateInsightInput(target_type="show", target_id=1))

    assert result is None


async def test_returns_the_cached_insight_for_a_show():
    cache = FakeInsightCache()
    key = build_insight_cache_key("show", 1, ["Drama", "Crime"], "A chemistry teacher.", 0, 0)
    await cache.set(key, "show", 1, _insight(), NOW)
    use_case, _cache = _use_case(cache=cache)

    result = await use_case.execute(GenerateInsightInput(target_type="show", target_id=1))

    assert result is not None
    assert result.text == "A tense drama."


async def test_returns_the_cached_insight_for_an_episode_using_parent_series_key():
    cache = FakeInsightCache()
    key = build_insight_cache_key(
        "episode", 42, ["Drama", "Crime"], "A teacher cooks.", 0, 0,
        series_summary="A chemistry teacher.",
    )
    await cache.set(key, "episode", 42, _insight("Gripping pilot."), NOW)
    show_repo = FakeShowReadModelRepository(shows=[_show()], episodes=[_episode()])
    use_case, _cache = _use_case(show_repo=show_repo, cache=cache)

    result = await use_case.execute(GenerateInsightInput(target_type="episode", target_id=42))

    assert result is not None
    assert result.text == "Gripping pilot."


async def test_raises_show_not_found_for_an_unknown_show():
    use_case, _cache = _use_case(show_repo=FakeShowReadModelRepository())

    with pytest.raises(ShowNotFound):
        await use_case.execute(GenerateInsightInput(target_type="show", target_id=999))


async def test_raises_episode_not_found_for_an_unknown_episode():
    use_case, _cache = _use_case(show_repo=FakeShowReadModelRepository())

    with pytest.raises(EpisodeNotFound):
        await use_case.execute(GenerateInsightInput(target_type="episode", target_id=999))
