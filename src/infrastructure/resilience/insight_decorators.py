from datetime import timedelta
import logging

from application.dto.insight_dto import InsightContext
from application.interfaces.clock import Clock
from application.interfaces.insight_cache import InsightCache
from application.interfaces.insight_generator import InsightGenerator
from domain.entities.insight import Insight
from infrastructure.resilience.bulkhead import Bulkhead
from infrastructure.resilience.circuit_breaker import CircuitBreaker
from infrastructure.resilience.retry_policy import RetryPolicy

logger = logging.getLogger(__name__)


class CachedInsightGenerator(InsightGenerator):
    def __init__(
        self, inner: InsightGenerator, cache: InsightCache, clock: Clock,
        ttl_seconds: int, fallback_ttl_seconds: int,
    ):
        self._inner = inner
        self._cache = cache
        self._clock = clock
        self._ttl_seconds = ttl_seconds
        self._fallback_ttl_seconds = fallback_ttl_seconds

    async def generate(self, context: InsightContext) -> Insight:
        cached = await self._cache.get(context.cache_key)
        if cached is not None:
            return cached

        insight = await self._inner.generate(context)
        ttl = self._fallback_ttl_seconds if insight.source == "fallback" else self._ttl_seconds
        expires_at = self._clock.now() + timedelta(seconds=ttl)
        await self._cache.set(context.cache_key, context.target_type, context.target_id, insight, expires_at)
        return insight


class FallbackInsightGenerator(InsightGenerator):
    def __init__(self, primary: InsightGenerator, fallback: InsightGenerator):
        self._primary = primary
        self._fallback = fallback

    async def generate(self, context: InsightContext) -> Insight:
        try:
            return await self._primary.generate(context)
        except Exception as exc:
            logger.warning("Insight provider failed; using fallback: %s", exc)
            return await self._fallback.generate(context)


class BreakingInsightGenerator(InsightGenerator):
    def __init__(self, inner: InsightGenerator, breaker: CircuitBreaker):
        self._inner = inner
        self._breaker = breaker

    async def generate(self, context: InsightContext) -> Insight:
        return await self._breaker.call(self._inner.generate, context)


class RetryingInsightGenerator(InsightGenerator):
    def __init__(self, inner: InsightGenerator, retry_policy: RetryPolicy):
        self._inner = inner
        self._retry_policy = retry_policy

    async def generate(self, context: InsightContext) -> Insight:
        return await self._retry_policy.run(self._inner.generate, context)


class BulkheadInsightGenerator(InsightGenerator):
    def __init__(self, inner: InsightGenerator, bulkhead: Bulkhead):
        self._inner = inner
        self._bulkhead = bulkhead

    async def generate(self, context: InsightContext) -> Insight:
        return await self._bulkhead.run(self._inner.generate, context)
