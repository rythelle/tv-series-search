from datetime import datetime

from application.interfaces.clock import Clock


class FakeClock(Clock):
    def __init__(self, now: datetime):
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now
