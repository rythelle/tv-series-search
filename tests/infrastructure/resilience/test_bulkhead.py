import asyncio

from infrastructure.resilience.bulkhead import Bulkhead


async def test_bounds_concurrent_executions():
    bulkhead = Bulkhead(max_concurrency=2)
    concurrent = 0
    max_seen = 0

    async def work():
        nonlocal concurrent, max_seen
        concurrent += 1
        max_seen = max(max_seen, concurrent)
        await asyncio.sleep(0.01)
        concurrent -= 1
        return "done"

    results = await asyncio.gather(*[bulkhead.run(work) for _ in range(6)])

    assert max_seen <= 2
    assert results == ["done"] * 6


async def test_propagates_exceptions_and_releases_the_slot():
    bulkhead = Bulkhead(max_concurrency=1)

    async def failing():
        raise RuntimeError("boom")

    async def succeeding():
        return "ok"

    try:
        await bulkhead.run(failing)
    except RuntimeError:
        pass

    assert await bulkhead.run(succeeding) == "ok"
