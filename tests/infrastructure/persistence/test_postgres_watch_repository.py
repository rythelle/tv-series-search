import uuid
from datetime import datetime, timezone

import pytest

from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.entities.watch_mark import WatchMark
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId
from domain.value_objects.viewer_id import ViewerId
from infrastructure.persistence.postgres_show_read_model_repository import (
    PostgresShowReadModelRepository,
)
from infrastructure.persistence.postgres_watch_repository import PostgresWatchRepository

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
VIEWER = ViewerId(str(uuid.uuid4()))


async def _seed_episode(pool, episode_id=10, show_id=1):
    show_repo = PostgresShowReadModelRepository(pool)
    await show_repo.upsert_shows(
        [
            Show(
                id=ShowId(show_id), name="Breaking Bad", premiered_year=2008, poster_url=None,
                summary="", genres=[], rating=None, popularity=1.0,
                details_fetched_at=NOW, episodes_fetched_at=NOW,
            )
        ]
    )
    await show_repo.upsert_episodes(
        ShowId(show_id),
        [
            Episode(
                id=EpisodeId(episode_id), show_id=ShowId(show_id), season=1, number=1,
                name="Pilot", airdate=None, runtime=None, summary="",
            )
        ],
    )


async def test_marking_then_listing_returns_the_episode(clean_pool):
    await _seed_episode(clean_pool)
    repo = PostgresWatchRepository(clean_pool)

    await repo.mark(WatchMark(viewer_id=VIEWER, episode_id=EpisodeId(10), watched_at=NOW))

    assert await repo.list_for_viewer(VIEWER, ShowId(1)) == {EpisodeId(10)}


async def test_marking_twice_is_idempotent(clean_pool):
    await _seed_episode(clean_pool)
    repo = PostgresWatchRepository(clean_pool)

    await repo.mark(WatchMark(viewer_id=VIEWER, episode_id=EpisodeId(10), watched_at=NOW))
    await repo.mark(WatchMark(viewer_id=VIEWER, episode_id=EpisodeId(10), watched_at=NOW))

    assert await repo.list_for_viewer(VIEWER, ShowId(1)) == {EpisodeId(10)}


async def test_unmarking_removes_it(clean_pool):
    await _seed_episode(clean_pool)
    repo = PostgresWatchRepository(clean_pool)
    await repo.mark(WatchMark(viewer_id=VIEWER, episode_id=EpisodeId(10), watched_at=NOW))

    await repo.unmark(VIEWER, EpisodeId(10))

    assert await repo.list_for_viewer(VIEWER, ShowId(1)) == set()


async def test_unmarking_when_never_marked_is_a_noop(clean_pool):
    await _seed_episode(clean_pool)
    repo = PostgresWatchRepository(clean_pool)

    await repo.unmark(VIEWER, EpisodeId(10))  # must not raise

    assert await repo.list_for_viewer(VIEWER, ShowId(1)) == set()
