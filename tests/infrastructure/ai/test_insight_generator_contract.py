from datetime import datetime, timezone

import httpx
import pytest

from application.dto.insight_dto import InsightContext
from domain.entities.insight import Insight
from domain.value_objects.insight_text import InsightText
from infrastructure.ai.anthropic_insight_generator import AnthropicInsightGenerator
from infrastructure.ai.heuristic_insight_generator import HeuristicInsightGenerator
from infrastructure.ai.huggingface_insight_generator import HuggingFaceInsightGenerator
from infrastructure.ai.openai_insight_generator import OpenAIInsightGenerator
from infrastructure.resilience.bulkhead import Bulkhead
from infrastructure.resilience.circuit_breaker import CircuitBreaker
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


def _context():
    return InsightContext(
        target_type="show", target_id=1, cache_key="k", genres=["Drama"],
        summary="A show.", recent_comments=[],
    )


def _ok_transport():
    def handler(request):
        return httpx.Response(200, json=_payload_for(request.url.host))

    return httpx.MockTransport(handler)


def _payload_for(host: str):
    if "huggingface" in host:
        return {"choices": [{"message": {"content": "ok"}}]}
    if "anthropic" in host:
        return {"content": [{"type": "text", "text": "ok"}]}
    return {"choices": [{"message": {"content": "ok"}}]}


def _build_heuristic():
    return HeuristicInsightGenerator(clock=FakeClock(NOW))


def _build_huggingface():
    client = httpx.AsyncClient(transport=_ok_transport())
    return HuggingFaceInsightGenerator(api_key="k", model="Qwen/Qwen2.5-7B-Instruct-1M", timeout_seconds=8, clock=FakeClock(NOW), client=client)


def _build_anthropic():
    client = httpx.AsyncClient(transport=_ok_transport(), base_url="https://api.anthropic.com")
    return AnthropicInsightGenerator(api_key="k", model="haiku", timeout_seconds=8, clock=FakeClock(NOW), client=client)


def _build_openai():
    client = httpx.AsyncClient(transport=_ok_transport(), base_url="https://api.openai.com")
    return OpenAIInsightGenerator(api_key="k", model="gpt-4o-mini", timeout_seconds=8, clock=FakeClock(NOW), client=client)


def _build_cached():
    inner = FakeInsightGenerator(insight=Insight(text=InsightText("ok"), source="llm", model="m", generated_at=NOW))
    return CachedInsightGenerator(inner, FakeInsightCache(), FakeClock(NOW), ttl_seconds=86400, fallback_ttl_seconds=300)


def _build_fallback():
    primary = FakeInsightGenerator(insight=Insight(text=InsightText("ok"), source="llm", model="m", generated_at=NOW))
    fallback = HeuristicInsightGenerator(clock=FakeClock(NOW))
    return FallbackInsightGenerator(primary, fallback)


def _build_breaking():
    inner = FakeInsightGenerator(insight=Insight(text=InsightText("ok"), source="llm", model="m", generated_at=NOW))
    return BreakingInsightGenerator(inner, CircuitBreaker(failure_threshold=3, cooldown_seconds=30, clock=FakeClock(NOW)))


def _build_retrying():
    inner = FakeInsightGenerator(insight=Insight(text=InsightText("ok"), source="llm", model="m", generated_at=NOW))
    return RetryingInsightGenerator(inner, RetryPolicy(max_retries=2, sleep=lambda s: _noop(), jitter=lambda: 0.0))


def _build_bulkhead():
    inner = FakeInsightGenerator(insight=Insight(text=InsightText("ok"), source="llm", model="m", generated_at=NOW))
    return BulkheadInsightGenerator(inner, Bulkhead(max_concurrency=2))


async def _noop():
    return None


IMPLEMENTATIONS = {
    "heuristic": _build_heuristic,
    "huggingface": _build_huggingface,
    "anthropic": _build_anthropic,
    "openai": _build_openai,
    "cached": _build_cached,
    "fallback": _build_fallback,
    "breaking": _build_breaking,
    "retrying": _build_retrying,
    "bulkhead": _build_bulkhead,
}


@pytest.mark.parametrize("name", list(IMPLEMENTATIONS))
async def test_every_insight_generator_satisfies_the_same_contract(name):
    generator = IMPLEMENTATIONS[name]()

    insight = await generator.generate(_context())

    assert isinstance(insight, Insight)
    assert isinstance(insight.text.value, str) and insight.text.value
    assert isinstance(insight.source, str) and insight.source
    assert insight.generated_at is not None
