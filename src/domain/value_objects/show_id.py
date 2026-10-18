from dataclasses import dataclass


@dataclass(frozen=True)
class ShowId:
    value: int

    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("show id must be positive")
