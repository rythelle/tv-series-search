from datetime import datetime, timedelta, timezone

import pytest

from domain.entities.insight import Insight
from domain.value_objects.insight_text import InsightText
from infrastructure.persistence.postgres_insight_cache import PostgresInsightCache

pytestmark = pytest.mark.integration

NOW = datetime.now(timezone.utc)


def _insight(text="A tense drama.", source="llm"):
    return Insight(text=InsightText(text), source=source, model="hf", generated_at=NOW)


async def test_returns_none_for_a_missing_key(clean_pool):
    cache = PostgresInsightCache(clean_pool)
    assert await cache.get("missing") is None


async def test_set_then_get_round_trips_before_expiry(clean_pool):
    cache = PostgresInsightCache(clean_pool)
    await cache.set("key-1", "show", 1, _insight(), NOW + timedelta(hours=1))

    result = await cache.get("key-1")

    assert result.text.value == "A tense drama."
    assert result.source == "llm"


async def test_an_expired_entry_is_not_served(clean_pool):
    cache = PostgresInsightCache(clean_pool)
    await cache.set("key-1", "show", 1, _insight(), NOW - timedelta(seconds=1))

    assert await cache.get("key-1") is None


async def test_set_overwrites_an_existing_key(clean_pool):
    cache = PostgresInsightCache(clean_pool)
    await cache.set("key-1", "show", 1, _insight("Old"), NOW + timedelta(hours=1))
    await cache.set("key-1", "show", 1, _insight("New"), NOW + timedelta(hours=1))

    result = await cache.get("key-1")
    assert result.text.value == "New"


async def test_invalidate_for_target_removes_matching_entries(clean_pool):
    cache = PostgresInsightCache(clean_pool)
    await cache.set("key-1", "show", 1, _insight(), NOW + timedelta(hours=1))
    await cache.set("key-2", "show", 2, _insight(), NOW + timedelta(hours=1))

    await cache.invalidate_for_target("show", 1)

    assert await cache.get("key-1") is None
    assert await cache.get("key-2") is not None
