from dataclasses import dataclass, field
from datetime import datetime

from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId


@dataclass
class Show:
    id: ShowId
    name: str
    premiered_year: int | None
    poster_url: str | None
    summary: str
    genres: list[Genre] = field(default_factory=list)
    rating: float | None = None
    popularity: float = 0.0
    details_fetched_at: datetime | None = None
    episodes_fetched_at: datetime | None = None
