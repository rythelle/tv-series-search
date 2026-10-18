import httpx

from application.interfaces.clock import Clock
from application.interfaces.insight_cache import InsightCache
from application.interfaces.insight_generator import InsightGenerator
from infrastructure.ai.anthropic_insight_generator import AnthropicInsightGenerator
from infrastructure.ai.gemini_insight_generator import GeminiInsightGenerator
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

_PROVIDERS = {
    "huggingface": HuggingFaceInsightGenerator,
    "anthropic": AnthropicInsightGenerator,
    "openai": OpenAIInsightGenerator,
    "gemini": GeminiInsightGenerator,
}


def build_insight_generator(
    provider: str, api_key: str, model: str, timeout_seconds: float, max_retries: int,
    breaker_failures: int, breaker_cooldown_seconds: float, max_concurrency: int,
    cache: InsightCache, cache_ttl_seconds: int, fallback_ttl_seconds: int,
    clock: Clock, http_client: httpx.AsyncClient,
) -> InsightGenerator:
    heuristic = HeuristicInsightGenerator(clock=clock)

    if not api_key or provider == "heuristic" or provider not in _PROVIDERS:
        return CachedInsightGenerator(heuristic, cache, clock, cache_ttl_seconds, fallback_ttl_seconds)

    provider_cls = _PROVIDERS[provider]
    raw_provider = provider_cls(
        api_key=api_key, model=model, timeout_seconds=timeout_seconds, clock=clock, client=http_client,
    )
    bulkheaded = BulkheadInsightGenerator(raw_provider, Bulkhead(max_concurrency))
    retried = RetryingInsightGenerator(bulkheaded, RetryPolicy(max_retries))
    breaking = BreakingInsightGenerator(
        retried, CircuitBreaker(breaker_failures, breaker_cooldown_seconds, clock)
    )
    with_fallback = FallbackInsightGenerator(primary=breaking, fallback=heuristic)
    return CachedInsightGenerator(with_fallback, cache, clock, cache_ttl_seconds, fallback_ttl_seconds)
