import httpx

from application.dto.insight_dto import InsightContext
from application.interfaces.clock import Clock
from application.interfaces.insight_generator import InsightGenerator
from domain.entities.insight import Insight
from domain.value_objects.insight_text import InsightText
from infrastructure.ai.errors import AIProviderError
from infrastructure.ai.prompt_builder import PromptBuilder


class AnthropicInsightGenerator(InsightGenerator):
    def __init__(
        self, api_key: str, model: str, timeout_seconds: float, clock: Clock,
        client: httpx.AsyncClient, prompt_builder: PromptBuilder | None = None,
    ):
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._clock = clock
        self._client = client
        self._prompt_builder = prompt_builder or PromptBuilder()

    async def generate(self, context: InsightContext) -> Insight:
        prompt = self._prompt_builder.build(context)
        try:
            response = await self._client.post(
                "/v1/messages",
                headers={"x-api-key": self._api_key, "anthropic-version": "2023-06-01"},
                json={
                    "model": self._model,
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=self._timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise AIProviderError(f"anthropic request failed: {exc}") from exc

        if response.status_code != 200:
            raise AIProviderError(f"anthropic returned status {response.status_code}")

        text = self._extract_text(response.json())
        if not text:
            raise AIProviderError("anthropic returned an empty generation")

        return Insight(text=InsightText(text), source="llm", model=self._model, generated_at=self._clock.now())

    @staticmethod
    def _extract_text(payload) -> str:
        blocks = payload.get("content") or []
        for block in blocks:
            if block.get("type") == "text" and block.get("text", "").strip():
                return block["text"].strip()
        return ""
