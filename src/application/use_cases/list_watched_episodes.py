from application.dto.watch_dto import ListWatchedEpisodesInput
from application.interfaces.watch_repository import WatchRepository
from domain.value_objects.show_id import ShowId
from domain.value_objects.viewer_id import ViewerId


class ListWatchedEpisodes:
    def __init__(self, repository: WatchRepository):
        self._repository = repository

    async def execute(self, input: ListWatchedEpisodesInput) -> set[int]:
        episode_ids = await self._repository.list_for_viewer(
            ViewerId(input.viewer_id), ShowId(input.show_id)
        )
        return {episode_id.value for episode_id in episode_ids}
