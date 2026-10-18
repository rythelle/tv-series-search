from datetime import datetime, timezone

import httpx
import pytest

from application.dto.insight_dto import InsightContext
from infrastructure.ai.errors import AIProviderError
from infrastructure.ai.openai_insight_generator import OpenAIInsightGenerator
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _context():
    return InsightContext(
        target_type="show", target_id=1, cache_key="k", genres=["Drama"],
        summary="A show.", recent_comments=[],
    )


def _generator(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.openai.com")
    return OpenAIInsightGenerator(
        api_key="secret", model="gpt-4o-mini", timeout_seconds=8, clock=FakeClock(NOW), client=client,
    )


async def test_returns_an_llm_insight_on_success():
    def handler(request):
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "A gripping drama."}}]},
        )

    insight = await _generator(handler).generate(_context())

    assert insight.text.value == "A gripping drama."
    assert insight.source == "llm"
    assert insight.model == "gpt-4o-mini"


async def test_raises_on_a_non_200_response():
    def handler(request):
        return httpx.Response(401)

    with pytest.raises(AIProviderError):
        await _generator(handler).generate(_context())


async def test_raises_when_no_choices_are_returned():
    def handler(request):
        return httpx.Response(200, json={"choices": []})

    with pytest.raises(AIProviderError):
        await _generator(handler).generate(_context())
