from application.interfaces.watch_repository import WatchRepository
from domain.entities.watch_mark import WatchMark
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId
from domain.value_objects.viewer_id import ViewerId


class FakeWatchRepository(WatchRepository):
    def __init__(self):
        self.marks: dict[tuple[str, int], WatchMark] = {}

    async def mark(self, mark: WatchMark) -> None:
        self.marks[(mark.viewer_id.value, mark.episode_id.value)] = mark

    async def unmark(self, viewer_id: ViewerId, episode_id: EpisodeId) -> None:
        self.marks.pop((viewer_id.value, episode_id.value), None)

    async def list_for_viewer(self, viewer_id: ViewerId, show_id: ShowId) -> set[EpisodeId]:
        return {
            mark.episode_id
            for (vid, _), mark in self.marks.items()
            if vid == viewer_id.value
        }
