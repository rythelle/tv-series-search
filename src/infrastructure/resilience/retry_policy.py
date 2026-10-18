import asyncio
import random
from collections.abc import Awaitable, Callable


class RetryPolicy:
    def __init__(
        self,
        max_retries: int,
        base_delay_seconds: float = 0.1,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        jitter: Callable[[], float] | None = None,
    ):
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._sleep = sleep or asyncio.sleep
        self._jitter = jitter or random.random

    async def run(self, fn, *args, **kwargs):
        attempt = 0
        while True:
            try:
                return await fn(*args, **kwargs)
            except Exception:
                attempt += 1
                if attempt > self._max_retries:
                    raise
                delay = self._base_delay_seconds * (2 ** (attempt - 1))
                delay += self._jitter() * self._base_delay_seconds
                await self._sleep(delay)
