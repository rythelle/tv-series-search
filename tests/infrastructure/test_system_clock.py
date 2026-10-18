from datetime import datetime, timezone

from infrastructure.system_clock import SystemClock


def test_now_returns_a_timezone_aware_utc_datetime():
    clock = SystemClock()
    before = datetime.now(timezone.utc)

    result = clock.now()

    assert result.tzinfo is not None
    assert result >= before
