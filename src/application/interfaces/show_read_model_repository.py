from abc import ABC, abstractmethod

from application.dto.show_dto import PopularCursor
from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId


class ShowReadModelRepository(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int, genre: Genre | None = None) -> list[Show]: ...

    @abstractmethod
    async def list_popular(
        self, limit: int, after: PopularCursor | None = None, genre: Genre | None = None
    ) -> list[Show]: ...

    @abstractmethod
    async def count_popular(self, genre: Genre | None = None) -> int: ...

    @abstractmethod
    async def list_genres(self) -> list[Genre]: ...

    @abstractmethod
    async def get_show(self, show_id: ShowId) -> Show | None: ...

    @abstractmethod
    async def get_episodes(self, show_id: ShowId) -> list[Episode]: ...

    @abstractmethod
    async def get_episode(self, episode_id: EpisodeId) -> Episode | None: ...

    @abstractmethod
    async def upsert_shows(self, shows: list[Show]) -> None: ...

    @abstractmethod
    async def upsert_episodes(self, show_id: ShowId, episodes: list[Episode]) -> None: ...
