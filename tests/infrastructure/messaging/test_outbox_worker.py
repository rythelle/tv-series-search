from infrastructure.messaging.outbox_worker import OutboxEvent, OutboxStore, OutboxWorker
from tests.fakes.insight_fakes import FakeInsightCache


class FakeOutboxStore(OutboxStore):
    def __init__(self, events: list[OutboxEvent]):
        self.events = list(events)
        self.processed: list[int] = []
        self.failures: list[int] = []

    async def fetch_unprocessed(self, max_attempts: int, limit: int) -> list[OutboxEvent]:
        return [e for e in self.events if e.attempts < max_attempts][:limit]

    async def mark_processed(self, event_id: int) -> None:
        self.processed.append(event_id)
        self.events = [e for e in self.events if e.id != event_id]

    async def record_failure(self, event_id: int) -> None:
        self.failures.append(event_id)
        for event in self.events:
            if event.id == event_id:
                event.attempts += 1


class _FailingInsightCache(FakeInsightCache):
    async def invalidate_for_target(self, target_type, target_id):
        raise RuntimeError("boom")


def _comment_posted_event(event_id=1, attempts=0):
    return OutboxEvent(
        id=event_id, type="CommentPosted",
        payload={"comment_id": 5, "target_type": "show", "target_id": 1}, attempts=attempts,
    )


async def test_invalidates_the_cache_for_a_commentposted_event_and_marks_it_processed():
    store = FakeOutboxStore(events=[_comment_posted_event()])
    cache = FakeInsightCache()
    worker = OutboxWorker(store=store, insight_cache=cache, poll_interval_seconds=2, max_attempts=5)

    processed = await worker.process_once()

    assert processed == 1
    assert cache.invalidated == [("show", 1)]
    assert store.processed == [1]


async def test_a_failing_invalidation_records_a_failure_and_leaves_it_unprocessed():
    store = FakeOutboxStore(events=[_comment_posted_event()])
    worker = OutboxWorker(
        store=store, insight_cache=_FailingInsightCache(), poll_interval_seconds=2, max_attempts=5,
    )

    processed = await worker.process_once()

    assert processed == 0
    assert store.processed == []
    assert store.failures == [1]


async def test_marks_an_unrecognized_event_type_processed_without_acting():
    event = OutboxEvent(id=1, type="SomethingFuture", payload={}, attempts=0)
    store = FakeOutboxStore(events=[event])
    cache = FakeInsightCache()
    worker = OutboxWorker(store=store, insight_cache=cache, poll_interval_seconds=2, max_attempts=5)

    processed = await worker.process_once()

    assert processed == 1
    assert cache.invalidated == []


async def test_process_once_returns_zero_when_nothing_is_pending():
    store = FakeOutboxStore(events=[])
    cache = FakeInsightCache()
    worker = OutboxWorker(store=store, insight_cache=cache, poll_interval_seconds=2, max_attempts=5)

    assert await worker.process_once() == 0
