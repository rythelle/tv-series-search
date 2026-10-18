from dataclasses import dataclass, field

from domain.entities.episode import Episode


@dataclass
class Season:
    number: int
    episodes: list[Episode] = field(default_factory=list)
