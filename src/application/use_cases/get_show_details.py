import asyncio

from application.dto.show_dto import GetShowDetailsInput, GetShowDetailsOutput
from application.errors import CatalogUnavailable
from application.interfaces.clock import Clock
from application.interfaces.show_catalog import ShowCatalog
from application.interfaces.show_read_model_repository import ShowReadModelRepository
from domain.errors import ShowNotFound
from domain.services.season_grouping import group_episodes_by_season
from domain.value_objects.show_id import ShowId


class GetShowDetails:
    def __init__(
        self,
        repository: ShowReadModelRepository,
        catalog: ShowCatalog,
        clock: Clock,
        stale_after_seconds: int = 86400,
    ):
        self._repository = repository
        self._catalog = catalog
        self._clock = clock
        self._stale_after_seconds = stale_after_seconds

    async def execute(self, input: GetShowDetailsInput) -> GetShowDetailsOutput:
        show_id = ShowId(input.show_id)
        local_show = await self._repository.get_show(show_id)

        if local_show and not self._is_stale(local_show):
            episodes = await self._repository.get_episodes(show_id)
            return GetShowDetailsOutput(
                show=local_show, seasons=group_episodes_by_season(episodes), degraded=False,
            )

        try:
            remote_show, remote_episodes = await asyncio.gather(
                self._catalog.get_show(show_id), self._catalog.get_episodes(show_id),
            )
        except CatalogUnavailable:
            if local_show:
                episodes = await self._repository.get_episodes(show_id)
                return GetShowDetailsOutput(
                    show=local_show, seasons=group_episodes_by_season(episodes), degraded=True,
                )
            raise ShowNotFound(input.show_id)

        now = self._clock.now()
        remote_show.details_fetched_at = now
        remote_show.episodes_fetched_at = now
        await self._repository.upsert_shows([remote_show])
        await self._repository.upsert_episodes(show_id, remote_episodes)
        return GetShowDetailsOutput(
            show=remote_show, seasons=group_episodes_by_season(remote_episodes), degraded=False,
        )

    def _is_stale(self, show) -> bool:
        if not show.details_fetched_at or not show.episodes_fetched_at:
            return True
        details_age = (self._clock.now() - show.details_fetched_at).total_seconds()
        episodes_age = (self._clock.now() - show.episodes_fetched_at).total_seconds()
        return max(details_age, episodes_age) > self._stale_after_seconds
