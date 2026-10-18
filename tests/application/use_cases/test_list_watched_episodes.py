from datetime import datetime, timezone

from application.dto.watch_dto import ListWatchedEpisodesInput
from application.use_cases.list_watched_episodes import ListWatchedEpisodes
from domain.entities.watch_mark import WatchMark
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.viewer_id import ViewerId
from tests.fakes.watch_fakes import FakeWatchRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
VIEWER = ViewerId("3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10")


async def test_returns_the_set_of_watched_episode_ids_for_the_viewer():
    repo = FakeWatchRepository()
    await repo.mark(WatchMark(viewer_id=VIEWER, episode_id=EpisodeId(10), watched_at=NOW))
    await repo.mark(WatchMark(viewer_id=VIEWER, episode_id=EpisodeId(11), watched_at=NOW))
    use_case = ListWatchedEpisodes(repository=repo)

    result = await use_case.execute(ListWatchedEpisodesInput(viewer_id=VIEWER.value, show_id=1))

    assert result == {10, 11}


async def test_returns_empty_set_when_nothing_watched():
    repo = FakeWatchRepository()
    use_case = ListWatchedEpisodes(repository=repo)

    result = await use_case.execute(ListWatchedEpisodesInput(viewer_id=VIEWER.value, show_id=1))

    assert result == set()
