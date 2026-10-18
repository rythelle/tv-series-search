from datetime import datetime, timezone

from application.interfaces.clock import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
