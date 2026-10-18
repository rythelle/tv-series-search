from datetime import datetime

from application.interfaces.clock import Clock


class BreakerOpen(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int, cooldown_seconds: float, clock: Clock):
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._failure_count = 0
        self._state = "closed"
        self._opened_at: datetime | None = None

    @property
    def state(self) -> str:
        return self._state

    async def call(self, fn, *args, **kwargs):
        if self._state == "open":
            if self._cooldown_elapsed():
                self._state = "half_open"
            else:
                raise BreakerOpen("circuit breaker is open")

        try:
            result = await fn(*args, **kwargs)
        except Exception:
            self._on_failure()
            raise

        self._on_success()
        return result

    def _cooldown_elapsed(self) -> bool:
        return (self._clock.now() - self._opened_at).total_seconds() >= self._cooldown_seconds

    def _on_failure(self) -> None:
        self._failure_count += 1
        if self._state == "half_open" or self._failure_count >= self._failure_threshold:
            self._state = "open"
            self._opened_at = self._clock.now()

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"
        self._opened_at = None
