from abc import ABC, abstractmethod

from domain.entities.watch_mark import WatchMark
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId
from domain.value_objects.viewer_id import ViewerId


class WatchRepository(ABC):
    @abstractmethod
    async def mark(self, mark: WatchMark) -> None: ...

    @abstractmethod
    async def unmark(self, viewer_id: ViewerId, episode_id: EpisodeId) -> None: ...

    @abstractmethod
    async def list_for_viewer(self, viewer_id: ViewerId, show_id: ShowId) -> set[EpisodeId]: ...
