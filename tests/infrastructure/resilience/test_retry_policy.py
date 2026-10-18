import pytest

from infrastructure.resilience.retry_policy import RetryPolicy


class _Flaky:
    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("boom")
        return "ok"


async def _no_sleep(_seconds: float) -> None:
    return None


async def test_succeeds_without_retrying_when_the_first_call_succeeds():
    policy = RetryPolicy(max_retries=2, sleep=_no_sleep, jitter=lambda: 0.0)
    fn = _Flaky(fail_times=0)

    assert await policy.run(fn) == "ok"
    assert fn.calls == 1


async def test_retries_up_to_the_configured_cap():
    policy = RetryPolicy(max_retries=2, sleep=_no_sleep, jitter=lambda: 0.0)
    fn = _Flaky(fail_times=2)

    assert await policy.run(fn) == "ok"
    assert fn.calls == 3


async def test_raises_after_exhausting_all_retries():
    policy = RetryPolicy(max_retries=2, sleep=_no_sleep, jitter=lambda: 0.0)
    fn = _Flaky(fail_times=99)

    with pytest.raises(RuntimeError):
        await policy.run(fn)
    assert fn.calls == 3


async def test_backs_off_with_increasing_delay():
    delays = []

    async def recording_sleep(seconds: float) -> None:
        delays.append(seconds)

    policy = RetryPolicy(max_retries=2, base_delay_seconds=0.1, sleep=recording_sleep, jitter=lambda: 0.0)
    fn = _Flaky(fail_times=2)

    await policy.run(fn)

    assert delays == [0.1, 0.2]
