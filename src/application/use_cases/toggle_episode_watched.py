from application.dto.watch_dto import ToggleEpisodeWatchedInput
from application.interfaces.clock import Clock
from application.interfaces.show_read_model_repository import ShowReadModelRepository
from application.interfaces.watch_repository import WatchRepository
from domain.entities.watch_mark import WatchMark
from domain.errors import EpisodeNotFound
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.viewer_id import ViewerId


class ToggleEpisodeWatched:
    def __init__(
        self,
        watch_repository: WatchRepository,
        show_repository: ShowReadModelRepository,
        clock: Clock,
    ):
        self._watch_repository = watch_repository
        self._show_repository = show_repository
        self._clock = clock

    async def execute(self, input: ToggleEpisodeWatchedInput) -> None:
        episode_id = EpisodeId(input.episode_id)
        viewer_id = ViewerId(input.viewer_id)

        episode = await self._show_repository.get_episode(episode_id)
        if episode is None:
            raise EpisodeNotFound(input.episode_id)

        if input.watched:
            await self._watch_repository.mark(
                WatchMark(viewer_id=viewer_id, episode_id=episode_id, watched_at=self._clock.now())
            )
        else:
            await self._watch_repository.unmark(viewer_id, episode_id)
