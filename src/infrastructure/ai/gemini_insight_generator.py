import httpx

from application.dto.insight_dto import InsightContext
from application.interfaces.clock import Clock
from application.interfaces.insight_generator import InsightGenerator
from domain.entities.insight import Insight
from domain.value_objects.insight_text import InsightText
from infrastructure.ai.errors import AIProviderError
from infrastructure.ai.prompt_builder import PromptBuilder


class GeminiInsightGenerator(InsightGenerator):
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
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self._model}:generateContent",
                headers={"x-goog-api-key": self._api_key},
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 240},
                },
                timeout=self._timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise AIProviderError(f"gemini request failed: {exc}") from exc

        if response.status_code != 200:
            raise AIProviderError(f"gemini returned status {response.status_code}")

        text = self._extract_text(response.json())
        if not text:
            raise AIProviderError("gemini returned an empty generation")

        return Insight(text=InsightText(text), source="llm", model=self._model, generated_at=self._clock.now())

    @staticmethod
    def _extract_text(payload) -> str:
        if not isinstance(payload, dict):
            return ""
        candidates = payload.get("candidates") or []
        if not candidates or not isinstance(candidates[0], dict):
            return ""
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return " ".join(
            part["text"].strip()
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str) and part["text"].strip()
        )
