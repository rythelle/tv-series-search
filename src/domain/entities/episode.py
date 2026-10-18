from dataclasses import dataclass

from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId


@dataclass
class Episode:
    id: EpisodeId
    show_id: ShowId
    season: int
    number: int | None
    name: str
    airdate: str | None
    runtime: int | None
    summary: str
