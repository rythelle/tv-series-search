from application.dto.show_dto import ListPopularShowsInput, ListPopularShowsOutput, PopularCursor
from application.interfaces.show_read_model_repository import ShowReadModelRepository
from domain.entities.show import Show
from domain.value_objects.genre import Genre


class ListPopularShows:
    def __init__(self, repository: ShowReadModelRepository):
        self._repository = repository

    async def execute(self, input: ListPopularShowsInput) -> ListPopularShowsOutput:
        genre = Genre(input.genre) if input.genre else None
        items = await self._repository.list_popular(input.limit, input.cursor, genre)
        total = await self._repository.count_popular(genre)
        return ListPopularShowsOutput(
            items=items, total=total, next_cursor=self._next_cursor(items, input.limit)
        )

    def _next_cursor(self, items: list[Show], limit: int) -> PopularCursor | None:
        # A page shorter than the limit is the end of the listing; only a full one
        # can have rows behind it.
        if not items or len(items) < limit:
            return None
        last = items[-1]
        return PopularCursor(popularity=last.popularity, show_id=last.id.value)
