from application.interfaces.show_read_model_repository import ShowReadModelRepository
from domain.value_objects.genre import Genre


class ListGenres:
    def __init__(self, repository: ShowReadModelRepository):
        self._repository = repository

    async def execute(self) -> list[Genre]:
        return await self._repository.list_genres()
