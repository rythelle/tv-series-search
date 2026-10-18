from abc import ABC, abstractmethod

from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.value_objects.show_id import ShowId


class ShowCatalog(ABC):
    @abstractmethod
    async def search(self, query: str) -> list[Show]: ...

    @abstractmethod
    async def list_page(self, page: int) -> list[Show]: ...

    @abstractmethod
    async def get_show(self, show_id: ShowId) -> Show: ...

    @abstractmethod
    async def get_episodes(self, show_id: ShowId) -> list[Episode]: ...
