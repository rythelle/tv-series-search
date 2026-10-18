from datetime import datetime, timezone

import httpx

from infrastructure.ai.heuristic_insight_generator import HeuristicInsightGenerator
from infrastructure.ai.insight_generator_factory import build_insight_generator
from infrastructure.resilience.insight_decorators import CachedInsightGenerator, FallbackInsightGenerator
from tests.fakes.clock import FakeClock
from tests.fakes.insight_fakes import FakeInsightCache

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _build(**overrides):
    defaults = dict(
        provider="huggingface", api_key="secret", model="gpt2", timeout_seconds=8,
        max_retries=2, breaker_failures=3, breaker_cooldown_seconds=60, max_concurrency=4,
        cache=FakeInsightCache(), cache_ttl_seconds=86400, fallback_ttl_seconds=300,
        clock=FakeClock(NOW), http_client=httpx.AsyncClient(),
    )
    defaults.update(overrides)
    return build_insight_generator(**defaults)


def test_returns_a_cached_fallback_wrapped_chain_when_an_api_key_is_present():
    generator = _build()
    assert isinstance(generator, CachedInsightGenerator)
    assert isinstance(generator._inner, FallbackInsightGenerator)


def test_gemini_uses_the_provider_chain_when_a_key_is_present():
    generator = _build(provider="gemini", model="gemini-3.5-flash-lite")
    assert isinstance(generator._inner, FallbackInsightGenerator)


def test_returns_a_cached_heuristic_only_chain_with_no_api_key():
    generator = _build(api_key="")
    assert isinstance(generator, CachedInsightGenerator)
    assert isinstance(generator._inner, HeuristicInsightGenerator)


def test_returns_a_cached_heuristic_only_chain_for_the_heuristic_provider():
    generator = _build(provider="heuristic", api_key="secret")
    assert isinstance(generator._inner, HeuristicInsightGenerator)
