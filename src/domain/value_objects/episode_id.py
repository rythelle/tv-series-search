from dataclasses import dataclass


@dataclass(frozen=True)
class EpisodeId:
    value: int

    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("episode id must be positive")
