from datetime import datetime, timezone
import json

import httpx
import pytest

from application.dto.insight_dto import InsightContext
from infrastructure.ai.errors import AIProviderError
from infrastructure.ai.gemini_insight_generator import GeminiInsightGenerator
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _context():
    return InsightContext(
        target_type="show", target_id=1, cache_key="k", genres=["Drama"],
        summary="A show.", recent_comments=[],
    )


def _generator(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return GeminiInsightGenerator(
        api_key="secret", model="gemini-3.5-flash-lite", timeout_seconds=8,
        clock=FakeClock(NOW), client=client,
    )


async def test_generates_insight_with_gemini_generate_content():
    def handler(request):
        assert str(request.url) == (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-3.5-flash-lite:generateContent"
        )
        assert request.headers["x-goog-api-key"] == "secret"
        body = json.loads(request.content)
        assert "Genres: Drama" in body["contents"][0]["parts"][0]["text"]
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "A gripping drama."}]}}],
        })

    insight = await _generator(handler).generate(_context())

    assert insight.text.value == "A gripping drama."
    assert insight.source == "llm"
    assert insight.model == "gemini-3.5-flash-lite"
    assert insight.generated_at == NOW


async def test_raises_on_provider_error():
    def handler(request):
        return httpx.Response(429)

    with pytest.raises(AIProviderError, match="429"):
        await _generator(handler).generate(_context())


async def test_raises_when_response_has_no_text():
    def handler(request):
        return httpx.Response(200, json={"candidates": [{"content": {"parts": []}}]})

    with pytest.raises(AIProviderError, match="empty generation"):
        await _generator(handler).generate(_context())


async def test_raises_on_transport_failure():
    def handler(request):
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(AIProviderError, match="request failed"):
        await _generator(handler).generate(_context())
