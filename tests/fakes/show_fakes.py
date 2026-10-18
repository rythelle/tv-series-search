from collections import Counter

from application.dto.show_dto import PopularCursor
from application.errors import CatalogUnavailable
from application.interfaces.show_catalog import ShowCatalog
from application.interfaces.show_read_model_repository import ShowReadModelRepository
from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId


class FakeShowReadModelRepository(ShowReadModelRepository):
    def __init__(self, shows: list[Show] | None = None, episodes: list[Episode] | None = None):
        self.shows: dict[int, Show] = {s.id.value: s for s in (shows or [])}
        self.episodes: dict[int, Episode] = {e.id.value: e for e in (episodes or [])}
        self.search_results: list[Show] = []
        self.search_calls: list[tuple[str, int, Genre | None]] = []

    async def search(self, query: str, limit: int, genre: Genre | None = None) -> list[Show]:
        self.search_calls.append((query, limit, genre))
        return _only_genre(self.search_results, genre)[:limit]

    async def list_popular(
        self, limit: int, after: PopularCursor | None = None, genre: Genre | None = None
    ) -> list[Show]:
        shows = _only_genre(list(self.shows.values()), genre)
        ordered = sorted(shows, key=lambda s: (-s.popularity, s.id.value))
        if after is not None:
            ordered = [
                show
                for show in ordered
                if show.popularity < after.popularity
                or (show.popularity == after.popularity and show.id.value > after.show_id)
            ]
        return ordered[:limit]

    async def count_popular(self, genre: Genre | None = None) -> int:
        return len(_only_genre(list(self.shows.values()), genre))

    async def list_genres(self) -> list[Genre]:
        counts = Counter(genre.value for show in self.shows.values() for genre in show.genres)
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [Genre(name) for name, _ in ordered]

    async def get_show(self, show_id: ShowId) -> Show | None:
        return self.shows.get(show_id.value)

    async def get_episodes(self, show_id: ShowId) -> list[Episode]:
        return [e for e in self.episodes.values() if e.show_id == show_id]

    async def get_episode(self, episode_id: EpisodeId) -> Episode | None:
        return self.episodes.get(episode_id.value)

    async def upsert_shows(self, shows: list[Show]) -> None:
        for show in shows:
            self.shows[show.id.value] = show

    async def upsert_episodes(self, show_id: ShowId, episodes: list[Episode]) -> None:
        for episode in episodes:
            self.episodes[episode.id.value] = episode


def _only_genre(shows: list[Show], genre: Genre | None) -> list[Show]:
    if genre is None:
        return list(shows)
    return [show for show in shows if genre in show.genres]


class FakeShowCatalog(ShowCatalog):
    def __init__(
        self,
        search_results: list[Show] | None = None,
        show: Show | None = None,
        episodes: list[Episode] | None = None,
        raises: Exception | None = None,
        pages: list[list[Show]] | None = None,
    ):
        self.search_results = search_results or []
        self.show = show
        self.episodes = episodes or []
        self.raises = raises
        self.pages = pages or []
        self.search_calls: list[str] = []
        self.page_calls: list[int] = []

    async def search(self, query: str) -> list[Show]:
        self.search_calls.append(query)
        if self.raises:
            raise self.raises
        return self.search_results

    async def list_page(self, page: int) -> list[Show]:
        self.page_calls.append(page)
        if self.raises:
            raise self.raises
        if page >= len(self.pages):
            raise CatalogUnavailable(f"tvmaze returned status 404 for page {page}")
        return self.pages[page]

    async def get_show(self, show_id):
        if self.raises:
            raise self.raises
        return self.show

    async def get_episodes(self, show_id):
        if self.raises:
            raise self.raises
        return self.episodes
