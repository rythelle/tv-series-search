from datetime import datetime, timezone

import httpx
import json
import pytest

from application.dto.insight_dto import InsightContext
from infrastructure.ai.errors import AIProviderError
from infrastructure.ai.huggingface_insight_generator import HuggingFaceInsightGenerator
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _context():
    return InsightContext(
        target_type="show", target_id=1, cache_key="k", genres=["Drama"],
        summary="A show.", recent_comments=[],
    )


def _generator(handler):
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )
    return HuggingFaceInsightGenerator(
        api_key="secret", model="Qwen/Qwen2.5-7B-Instruct-1M", timeout_seconds=8,
        clock=FakeClock(NOW), client=client,
    )


async def test_returns_an_llm_insight_on_success():
    def handler(request):
        assert request.headers["authorization"] == "Bearer secret"
        assert str(request.url) == "https://router.huggingface.co/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"] == "Qwen/Qwen2.5-7B-Instruct-1M"
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"
        assert "Genres: Drama" in payload["messages"][0]["content"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "A gripping drama."}}]})

    insight = await _generator(handler).generate(_context())

    assert insight.text.value == "A gripping drama."
    assert insight.source == "llm"
    assert insight.model == "Qwen/Qwen2.5-7B-Instruct-1M"
    assert insight.generated_at == NOW


async def test_raises_on_a_non_200_response():
    def handler(request):
        return httpx.Response(503)

    with pytest.raises(AIProviderError):
        await _generator(handler).generate(_context())


async def test_raises_on_an_empty_generation():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    with pytest.raises(AIProviderError):
        await _generator(handler).generate(_context())


async def test_raises_on_a_transport_failure():
    def handler(request):
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(AIProviderError):
        await _generator(handler).generate(_context())
