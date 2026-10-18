from datetime import datetime, timezone

import pytest

from application.dto.watch_dto import ToggleEpisodeWatchedInput
from application.use_cases.toggle_episode_watched import ToggleEpisodeWatched
from domain.entities.episode import Episode
from domain.errors import EpisodeNotFound
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId
from tests.fakes.clock import FakeClock
from tests.fakes.show_fakes import FakeShowReadModelRepository
from tests.fakes.watch_fakes import FakeWatchRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
VIEWER = "3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10"


def _episode(episode_id=10):
    return Episode(
        id=EpisodeId(episode_id), show_id=ShowId(1), season=1, number=1, name="Pilot",
        airdate=None, runtime=None, summary="",
    )


async def test_marks_an_episode_watched():
    show_repo = FakeShowReadModelRepository(episodes=[_episode()])
    watch_repo = FakeWatchRepository()
    use_case = ToggleEpisodeWatched(watch_repository=watch_repo, show_repository=show_repo, clock=FakeClock(NOW))

    await use_case.execute(ToggleEpisodeWatchedInput(viewer_id=VIEWER, episode_id=10, watched=True))

    assert watch_repo.marks[(VIEWER, 10)].watched_at == NOW


async def test_marking_twice_is_idempotent():
    show_repo = FakeShowReadModelRepository(episodes=[_episode()])
    watch_repo = FakeWatchRepository()
    use_case = ToggleEpisodeWatched(watch_repository=watch_repo, show_repository=show_repo, clock=FakeClock(NOW))

    await use_case.execute(ToggleEpisodeWatchedInput(viewer_id=VIEWER, episode_id=10, watched=True))
    await use_case.execute(ToggleEpisodeWatchedInput(viewer_id=VIEWER, episode_id=10, watched=True))

    assert len(watch_repo.marks) == 1


async def test_unmarking_removes_the_mark():
    show_repo = FakeShowReadModelRepository(episodes=[_episode()])
    watch_repo = FakeWatchRepository()
    use_case = ToggleEpisodeWatched(watch_repository=watch_repo, show_repository=show_repo, clock=FakeClock(NOW))
    await use_case.execute(ToggleEpisodeWatchedInput(viewer_id=VIEWER, episode_id=10, watched=True))

    await use_case.execute(ToggleEpisodeWatchedInput(viewer_id=VIEWER, episode_id=10, watched=False))

    assert watch_repo.marks == {}


async def test_unmarking_when_never_marked_is_a_noop():
    show_repo = FakeShowReadModelRepository(episodes=[_episode()])
    watch_repo = FakeWatchRepository()
    use_case = ToggleEpisodeWatched(watch_repository=watch_repo, show_repository=show_repo, clock=FakeClock(NOW))

    await use_case.execute(ToggleEpisodeWatchedInput(viewer_id=VIEWER, episode_id=10, watched=False))

    assert watch_repo.marks == {}


async def test_raises_episode_not_found_for_an_unknown_episode():
    show_repo = FakeShowReadModelRepository()
    watch_repo = FakeWatchRepository()
    use_case = ToggleEpisodeWatched(watch_repository=watch_repo, show_repository=show_repo, clock=FakeClock(NOW))

    with pytest.raises(EpisodeNotFound):
        await use_case.execute(ToggleEpisodeWatchedInput(viewer_id=VIEWER, episode_id=999, watched=True))
