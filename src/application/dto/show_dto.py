from dataclasses import dataclass

from domain.entities.season import Season
from domain.entities.show import Show


@dataclass
class SearchShowsInput:
    query: str
    limit: int
    genre: str | None = None


@dataclass
class SearchShowsOutput:
    items: list[Show]
    degraded: bool


@dataclass(frozen=True)
class PopularCursor:
    """A position in the popularity ranking, as the last row handed out.

    The listing cannot use OFFSET. Rows arrive mid-scroll -- the catalog is
    deepened from the TVMaze index while the reader is still scrolling -- and a
    row landing above the reader's position shifts every later offset by one, so
    the next page repeats a show (or drops one when a row is removed). Naming the
    last row seen instead makes the next page "whatever sorts after this",
    whatever was inserted above it.
    """

    popularity: float
    show_id: int

    def encode(self) -> str:
        return f"{self.popularity}:{self.show_id}"

    @classmethod
    def parse(cls, raw: str) -> "PopularCursor":
        popularity, _, show_id = raw.partition(":")
        try:
            return cls(popularity=float(popularity), show_id=int(show_id))
        except ValueError:
            raise ValueError(f"cursor is not a listing position: {raw!r}") from None


@dataclass
class ListPopularShowsInput:
    limit: int
    cursor: PopularCursor | None = None
    genre: str | None = None


@dataclass
class ListPopularShowsOutput:
    items: list[Show]
    total: int
    next_cursor: PopularCursor | None = None


@dataclass
class GetShowDetailsInput:
    show_id: int


@dataclass
class GetShowDetailsOutput:
    show: Show
    seasons: list[Season]
    degraded: bool
