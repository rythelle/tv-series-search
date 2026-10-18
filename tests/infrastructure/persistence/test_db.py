import pytest

from infrastructure.persistence.db import wait_for_database


async def _no_sleep(_seconds: float) -> None:
    return None


async def test_returns_the_connection_on_the_first_successful_attempt():
    async def connect():
        return "pool"

    assert await wait_for_database(connect, sleep=_no_sleep) == "pool"


async def test_retries_until_the_connection_succeeds():
    attempts = []

    async def connect():
        attempts.append(1)
        if len(attempts) < 3:
            raise OSError("not ready")
        return "pool"

    assert await wait_for_database(connect, sleep=_no_sleep) == "pool"
    assert len(attempts) == 3


async def test_raises_after_exhausting_all_attempts():
    async def connect():
        raise OSError("never ready")

    with pytest.raises(RuntimeError):
        await wait_for_database(connect, max_attempts=3, sleep=_no_sleep)
