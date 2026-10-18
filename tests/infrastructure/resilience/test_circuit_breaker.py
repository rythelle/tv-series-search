from datetime import datetime, timedelta, timezone

import pytest

from infrastructure.resilience.circuit_breaker import BreakerOpen, CircuitBreaker
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _Failing:
    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("boom")
        return "ok"


async def test_stays_closed_below_the_failure_threshold():
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30, clock=FakeClock(NOW))
    fn = _Failing(fail_times=2)

    with pytest.raises(RuntimeError):
        await breaker.call(fn)
    with pytest.raises(RuntimeError):
        await breaker.call(fn)

    assert breaker.state == "closed"
    assert await breaker.call(fn) == "ok"


async def test_opens_after_consecutive_failures_reach_the_threshold():
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=30, clock=FakeClock(NOW))
    fn = _Failing(fail_times=5)

    with pytest.raises(RuntimeError):
        await breaker.call(fn)
    with pytest.raises(RuntimeError):
        await breaker.call(fn)

    assert breaker.state == "open"


async def test_rejects_calls_without_invoking_the_function_while_open():
    clock = FakeClock(NOW)
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30, clock=clock)
    fn = _Failing(fail_times=99)

    with pytest.raises(RuntimeError):
        await breaker.call(fn)

    calls_before = fn.calls
    with pytest.raises(BreakerOpen):
        await breaker.call(fn)

    assert fn.calls == calls_before


async def test_half_opens_after_the_cooldown_and_closes_on_success():
    clock = FakeClock(NOW)
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30, clock=clock)
    fn = _Failing(fail_times=1)

    with pytest.raises(RuntimeError):
        await breaker.call(fn)

    clock.set(NOW + timedelta(seconds=31))

    assert await breaker.call(fn) == "ok"
    assert breaker.state == "closed"


async def test_a_failed_half_open_trial_reopens_the_breaker():
    clock = FakeClock(NOW)
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30, clock=clock)
    fn = _Failing(fail_times=99)

    with pytest.raises(RuntimeError):
        await breaker.call(fn)

    clock.set(NOW + timedelta(seconds=31))

    with pytest.raises(RuntimeError):
        await breaker.call(fn)

    assert breaker.state == "open"
