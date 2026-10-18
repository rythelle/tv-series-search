from pydantic import BaseModel

from domain.entities.episode import Episode
from domain.entities.season import Season
from domain.entities.show import Show


class ShowSummarySchema(BaseModel):
    id: int
    name: str
    premiered_year: int | None
    poster_url: str | None
    summary: str
    genres: list[str]
    rating: float | None
    popularity: float

    @classmethod
    def from_domain(cls, show: Show) -> "ShowSummarySchema":
        return cls(
            id=show.id.value, name=show.name, premiered_year=show.premiered_year,
            poster_url=show.poster_url, summary=show.summary,
            genres=[genre.value for genre in show.genres], rating=show.rating,
            popularity=show.popularity,
        )


class SearchResponseSchema(BaseModel):
    items: list[ShowSummarySchema]
    degraded: bool


class PopularResponseSchema(BaseModel):
    items: list[ShowSummarySchema]
    degraded: bool
    # Rows matching the filter that are stored right now. It is a count for the
    # reader, not a stopping rule -- the catalog grows as the listing is paged,
    # so `next_cursor` is what says whether more exist.
    total: int
    # Opaque position to pass back as ?cursor= for the next page; null at the end
    # of the list.
    next_cursor: str | None = None


class GenresResponseSchema(BaseModel):
    items: list[str]


class EpisodeSchema(BaseModel):
    id: int
    season: int
    number: int | None
    name: str
    airdate: str | None
    runtime: int | None
    summary: str

    @classmethod
    def from_domain(cls, episode: Episode) -> "EpisodeSchema":
        return cls(
            id=episode.id.value, season=episode.season, number=episode.number,
            name=episode.name, airdate=episode.airdate, runtime=episode.runtime,
            summary=episode.summary,
        )


class SeasonSchema(BaseModel):
    number: int
    episodes: list[EpisodeSchema]

    @classmethod
    def from_domain(cls, season: Season) -> "SeasonSchema":
        return cls(
            number=season.number,
            episodes=[EpisodeSchema.from_domain(episode) for episode in season.episodes],
        )


class ShowDetailsResponseSchema(BaseModel):
    show: ShowSummarySchema
    seasons: list[SeasonSchema]
    degraded: bool
