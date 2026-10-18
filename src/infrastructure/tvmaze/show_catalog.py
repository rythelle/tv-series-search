import logging

import httpx

from application.errors import CatalogUnavailable
from application.interfaces.show_catalog import ShowCatalog
from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.value_objects.show_id import ShowId
from infrastructure.resilience.circuit_breaker import BreakerOpen, CircuitBreaker
from infrastructure.tvmaze.mappers import map_episode, map_show

logger = logging.getLogger(__name__)


class TVMazeShowCatalog(ShowCatalog):
    def __init__(self, client: httpx.AsyncClient, timeout_seconds: float, breaker: CircuitBreaker):
        self._client = client
        self._timeout_seconds = timeout_seconds
        self._breaker = breaker

    async def search(self, query: str) -> list[Show]:
        payload = await self._get("/search/shows", params={"q": query})
        return [map_show(item["show"]) for item in payload]

    async def list_page(self, page: int) -> list[Show]:
        payload = await self._get("/shows", params={"page": page})
        return [map_show(item) for item in payload]

    async def get_show(self, show_id: ShowId) -> Show:
        payload = await self._get(f"/shows/{show_id.value}")
        return map_show(payload)

    async def get_episodes(self, show_id: ShowId) -> list[Episode]:
        payload = await self._get(f"/shows/{show_id.value}/episodes")
        return [map_episode(item, show_id) for item in payload]

    async def _get(self, path: str, params: dict | None = None):
        try:
            response = await self._breaker.call(self._request, path, params)
        except (httpx.HTTPError, BreakerOpen) as exc:
            # Callers answer 200 with degraded=true, so from the server side the
            # outage leaves no trace otherwise: httpx logs the request only once
            # a response comes back, and a timeout never gets one. %r because a
            # timeout's str() is routinely empty -- the class name is the signal.
            logger.warning("TVMaze request to %s failed: %r", path, exc)
            raise CatalogUnavailable(str(exc)) from exc
        return response.json()

    async def _request(self, path: str, params: dict | None) -> httpx.Response:
        response = await self._client.get(path, params=params, timeout=self._timeout_seconds)
        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"tvmaze returned status {response.status_code}",
                request=response.request,
                response=response,
            )
        return response
