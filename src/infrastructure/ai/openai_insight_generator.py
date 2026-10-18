import httpx

from application.dto.insight_dto import InsightContext
from application.interfaces.clock import Clock
from application.interfaces.insight_generator import InsightGenerator
from domain.entities.insight import Insight
from domain.value_objects.insight_text import InsightText
from infrastructure.ai.errors import AIProviderError
from infrastructure.ai.prompt_builder import PromptBuilder


class OpenAIInsightGenerator(InsightGenerator):
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
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "messages": [{"role": "user", "content": prompt}]},
                timeout=self._timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise AIProviderError(f"openai request failed: {exc}") from exc

        if response.status_code != 200:
            raise AIProviderError(f"openai returned status {response.status_code}")

        text = self._extract_text(response.json())
        if not text:
            raise AIProviderError("openai returned an empty generation")

        return Insight(text=InsightText(text), source="llm", model=self._model, generated_at=self._clock.now())

    @staticmethod
    def _extract_text(payload) -> str:
        choices = payload.get("choices") or []
        if not choices:
            return ""
        return (choices[0].get("message", {}).get("content") or "").strip()
