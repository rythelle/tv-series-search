from datetime import datetime, timedelta, timezone

from infrastructure.resilience.ttl_cache import TtlCache
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_returns_none_for_a_missing_key():
    cache = TtlCache(ttl_seconds=60, clock=FakeClock(NOW))
    assert cache.get("missing") is None


def test_returns_a_value_before_it_expires():
    clock = FakeClock(NOW)
    cache = TtlCache(ttl_seconds=60, clock=clock)
    cache.set("q", ["result"])

    clock.set(NOW + timedelta(seconds=30))

    assert cache.get("q") == ["result"]


def test_returns_none_after_the_ttl_elapses():
    clock = FakeClock(NOW)
    cache = TtlCache(ttl_seconds=60, clock=clock)
    cache.set("q", ["result"])

    clock.set(NOW + timedelta(seconds=61))

    assert cache.get("q") is None


def test_set_overwrites_an_existing_value():
    cache = TtlCache(ttl_seconds=60, clock=FakeClock(NOW))
    cache.set("q", ["old"])
    cache.set("q", ["new"])

    assert cache.get("q") == ["new"]
