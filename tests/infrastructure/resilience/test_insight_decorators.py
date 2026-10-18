from datetime import datetime, timedelta, timezone

import pytest

from application.dto.insight_dto import InsightContext
from domain.entities.insight import Insight
from domain.value_objects.insight_text import InsightText
from infrastructure.resilience.bulkhead import Bulkhead
from infrastructure.resilience.circuit_breaker import BreakerOpen, CircuitBreaker
from infrastructure.resilience.insight_decorators import (
    BreakingInsightGenerator,
    BulkheadInsightGenerator,
    CachedInsightGenerator,
    FallbackInsightGenerator,
    RetryingInsightGenerator,
)
from infrastructure.resilience.retry_policy import RetryPolicy
from tests.fakes.clock import FakeClock
from tests.fakes.insight_fakes import FakeInsightCache, FakeInsightGenerator

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _context(cache_key="k"):
    return InsightContext(
        target_type="show", target_id=1, cache_key=cache_key, genres=["Drama"],
        summary="A show.", recent_comments=[],
    )


def _insight(source="llm"):
    return Insight(text=InsightText("A tense drama."), source=source, model="hf", generated_at=NOW)


async def test_cached_returns_the_cached_value_without_calling_inner():
    cache = FakeInsightCache()
    cache.store["k"] = _insight()
    inner = FakeInsightGenerator(insight=_insight())
    generator = CachedInsightGenerator(inner, cache, FakeClock(NOW), ttl_seconds=86400, fallback_ttl_seconds=300)

    result = await generator.generate(_context())

    assert result.text.value == "A tense drama."
    assert inner.calls == []


async def test_cached_stores_an_llm_result_with_the_full_ttl():
    cache = FakeInsightCache()
    inner = FakeInsightGenerator(insight=_insight(source="llm"))
    generator = CachedInsightGenerator(inner, cache, FakeClock(NOW), ttl_seconds=86400, fallback_ttl_seconds=300)

    await generator.generate(_context())

    *_, expires_at = cache.sets[0]
    assert expires_at == NOW + timedelta(seconds=86400)


async def test_cached_stores_a_fallback_result_with_the_shorter_ttl():
    cache = FakeInsightCache()
    inner = FakeInsightGenerator(insight=_insight(source="fallback"))
    generator = CachedInsightGenerator(inner, cache, FakeClock(NOW), ttl_seconds=86400, fallback_ttl_seconds=300)

    await generator.generate(_context())

    *_, expires_at = cache.sets[0]
    assert expires_at == NOW + timedelta(seconds=300)


async def test_fallback_returns_the_primarys_result_on_success():
    primary = FakeInsightGenerator(insight=_insight(source="llm"))
    fallback = FakeInsightGenerator(insight=_insight(source="fallback"))
    generator = FallbackInsightGenerator(primary, fallback)

    result = await generator.generate(_context())

    assert result.source == "llm"
    assert fallback.calls == []


async def test_fallback_delegates_when_the_primary_raises(caplog):
    primary = FakeInsightGenerator(raises=RuntimeError("boom"))
    fallback = FakeInsightGenerator(insight=_insight(source="fallback"))
    generator = FallbackInsightGenerator(primary, fallback)

    result = await generator.generate(_context())

    assert result.source == "fallback"
    assert "boom" in caplog.text


async def test_breaking_raises_breaker_open_once_the_breaker_trips():
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30, clock=FakeClock(NOW))
    inner = FakeInsightGenerator(raises=RuntimeError("boom"))
    generator = BreakingInsightGenerator(inner, breaker)

    with pytest.raises(RuntimeError):
        await generator.generate(_context())

    calls_before = len(inner.calls)
    with pytest.raises(BreakerOpen):
        await generator.generate(_context())
    assert len(inner.calls) == calls_before


async def test_retrying_retries_up_to_the_policy_cap():
    class _FlakyTwice(FakeInsightGenerator):
        async def generate(self, context):
            self.calls.append(context)
            if len(self.calls) < 3:
                raise RuntimeError("boom")
            return self.insight

    inner = _FlakyTwice(insight=_insight())
    policy = RetryPolicy(max_retries=2, sleep=lambda s: _no_sleep(), jitter=lambda: 0.0)
    generator = RetryingInsightGenerator(inner, policy)

    result = await generator.generate(_context())

    assert result.source == "llm"
    assert len(inner.calls) == 3


async def test_bulkhead_delegates_to_the_wrapped_bulkhead():
    bulkhead = Bulkhead(max_concurrency=1)
    inner = FakeInsightGenerator(insight=_insight())
    generator = BulkheadInsightGenerator(inner, bulkhead)

    result = await generator.generate(_context())

    assert result.source == "llm"
    assert len(inner.calls) == 1


async def _no_sleep():
    return None
