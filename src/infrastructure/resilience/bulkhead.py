import asyncio


class Bulkhead:
    def __init__(self, max_concurrency: int):
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run(self, fn, *args, **kwargs):
        async with self._semaphore:
            return await fn(*args, **kwargs)
