from datetime import datetime, timezone

from application.dto.insight_dto import InsightContext
from infrastructure.ai.heuristic_insight_generator import HeuristicInsightGenerator
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def test_returns_a_real_sentence_labelled_fallback():
    generator = HeuristicInsightGenerator(clock=FakeClock(NOW))
    context = InsightContext(
        target_type="show", target_id=1, cache_key="k", genres=["Drama"],
        summary="A chemistry teacher turns to crime.", recent_comments=["I love this show"],
    )

    insight = await generator.generate(context)

    assert insight.source == "fallback"
    assert insight.model is None
    assert insight.generated_at == NOW
    assert "Drama" in insight.text.value


async def test_describes_an_episode_target_as_an_episode():
    generator = HeuristicInsightGenerator(clock=FakeClock(NOW))
    context = InsightContext(
        target_type="episode", target_id=42, cache_key="k", genres=["Drama"],
        summary="A teacher cooks.", recent_comments=[], series_summary="A chemistry teacher.",
    )

    insight = await generator.generate(context)

    assert "episode" in insight.text.value.lower()
