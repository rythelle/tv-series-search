from application.dto.show_dto import SearchShowsInput, SearchShowsOutput
from application.errors import CatalogUnavailable
from application.interfaces.clock import Clock
from application.interfaces.show_catalog import ShowCatalog
from application.interfaces.show_read_model_repository import ShowReadModelRepository
from domain.entities.show import Show
from domain.value_objects.genre import Genre


class SearchShows:
    def __init__(
        self,
        repository: ShowReadModelRepository,
        catalog: ShowCatalog,
        clock: Clock,
    ):
        self._repository = repository
        self._catalog = catalog
        self._clock = clock

    async def execute(self, input: SearchShowsInput) -> SearchShowsOutput:
        genre = Genre(input.genre) if input.genre else None
        local_hits = await self._repository.search(input.query, input.limit, genre)

        # Both sources are always consulted. The read model holds a slice of the
        # catalog, so local hits prove a stored row matched -- never that nothing
        # else does. Short-circuiting on a fresh local hit answered "dex" with the
        # one stored Dexter and hid Dino Dex and Dex Hamilton entirely.
        try:
            remote_hits = await self._catalog.search(input.query)
        except CatalogUnavailable:
            return SearchShowsOutput(items=local_hits, degraded=True)

        self._stamp_fetched_now(remote_hits)
        await self._repository.upsert_shows(remote_hits)
        merged = self._merge(local_hits, self._only_genre(remote_hits, genre))
        return SearchShowsOutput(items=merged[: input.limit], degraded=False)

    def _merge(self, local_hits: list[Show], remote_hits: list[Show]) -> list[Show]:
        # Local ranking leads: it scores title similarity against popularity, while
        # the catalog orders by its own opaque score. A show both sources returned
        # keeps the local position but the freshly fetched copy, which is the
        # authoritative one.
        remote_by_id = {show.id.value: show for show in remote_hits}
        merged = [remote_by_id.get(show.id.value, show) for show in local_hits]
        seen = {show.id.value for show in merged}
        merged.extend(show for show in remote_hits if show.id.value not in seen)
        return merged

    def _only_genre(self, shows: list[Show], genre: Genre | None) -> list[Show]:
        if genre is None:
            return shows
        return [show for show in shows if genre in show.genres]

    def _stamp_fetched_now(self, shows: list[Show]) -> None:
        now = self._clock.now()
        for show in shows:
            show.details_fetched_at = now
