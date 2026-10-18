import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ViewerId:
    value: str

    def __post_init__(self):
        canonical = uuid.UUID(self.value)  # raises ValueError on malformed input
        object.__setattr__(self, "value", str(canonical))
