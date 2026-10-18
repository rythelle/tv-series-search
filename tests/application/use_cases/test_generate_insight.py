from datetime import datetime, timezone

import pytest

from application.dto.insight_dto import GenerateInsightInput
from application.insight_cache_key import build_insight_cache_key
from application.use_cases.generate_insight import GenerateInsight
from domain.entities.episode import Episode
from domain.entities.insight import Insight
from domain.entities.show import Show
from domain.errors import EpisodeNotFound, ShowNotFound
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.insight_text import InsightText
from domain.value_objects.show_id import ShowId
from tests.fakes.comment_fakes import FakeCommentRepository
from tests.fakes.insight_fakes import FakeInsightGenerator
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


def _use_case(show_repo=None, comment_repo=None, insight=None):
    show_repo = show_repo or FakeShowReadModelRepository(shows=[_show()])
    comment_repo = comment_repo or FakeCommentRepository()
    generator = FakeInsightGenerator(
        insight or Insight(text=InsightText("A tense drama."), source="llm", model="hf", generated_at=NOW)
    )
    use_case = GenerateInsight(
        show_repository=show_repo, comment_repository=comment_repo, insight_generator=generator,
    )
    return use_case, show_repo, comment_repo, generator


async def test_delegates_to_the_generator_and_returns_its_output():
    use_case, *_, generator = _use_case()

    result = await use_case.execute(GenerateInsightInput(target_type="show", target_id=1))

    assert result.text == "A tense drama."
    assert result.source == "llm"
    assert result.model == "hf"
    assert len(generator.calls) == 1


async def test_builds_the_context_with_the_subjects_genres_summary_and_cache_key():
    use_case, _show_repo, _comment_repo, generator = _use_case()

    await use_case.execute(GenerateInsightInput(target_type="show", target_id=1))

    context = generator.calls[0]
    assert context.genres == ["Drama", "Crime"]
    assert context.summary == "A chemistry teacher."
    assert context.series_summary is None
    assert context.cache_key == build_insight_cache_key(
        "show", 1, ["Drama", "Crime"], "A chemistry teacher.", 0, 0
    )


async def test_raises_show_not_found_for_an_unknown_show():
    use_case, *_ = _use_case(show_repo=FakeShowReadModelRepository())

    with pytest.raises(ShowNotFound):
        await use_case.execute(GenerateInsightInput(target_type="show", target_id=999))


async def test_builds_episode_context_with_its_summary_and_parent_series_genres():
    show_repo = FakeShowReadModelRepository(shows=[_show()], episodes=[_episode()])
    use_case, *_, generator = _use_case(show_repo=show_repo)

    await use_case.execute(GenerateInsightInput(target_type="episode", target_id=42))

    context = generator.calls[0]
    assert context.summary == "A teacher cooks."
    assert context.genres == ["Drama", "Crime"]
    assert context.series_summary == "A chemistry teacher."
    assert context.cache_key == build_insight_cache_key(
        "episode", 42, ["Drama", "Crime"], "A teacher cooks.", 0, 0,
        series_summary="A chemistry teacher.",
    )


async def test_episode_insight_falls_back_to_no_genres_when_parent_series_is_missing():
    show_repo = FakeShowReadModelRepository(episodes=[_episode()])
    use_case, *_, generator = _use_case(show_repo=show_repo)

    await use_case.execute(GenerateInsightInput(target_type="episode", target_id=42))

    context = generator.calls[0]
    assert context.summary == "A teacher cooks."
    assert context.genres == []
    assert context.series_summary is None


async def test_raises_episode_not_found_for_an_unknown_episode():
    use_case, *_ = _use_case(show_repo=FakeShowReadModelRepository())

    with pytest.raises(EpisodeNotFound):
        await use_case.execute(GenerateInsightInput(target_type="episode", target_id=999))
