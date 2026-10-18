import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


async def wait_for_database(
    connect: Callable[[], Awaitable[Any]],
    max_attempts: int = 30,
    delay_seconds: float = 1.0,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> Any:
    sleep = sleep or asyncio.sleep
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            return await connect()
        except Exception as exc:
            last_error = exc
            await sleep(delay_seconds)
    raise RuntimeError(f"database not reachable after {max_attempts} attempts") from last_error
