from dataclasses import dataclass


@dataclass(frozen=True, eq=False)
class Genre:
    value: str

    def __post_init__(self):
        stripped = self.value.strip()
        if not stripped:
            raise ValueError("genre must not be blank")
        object.__setattr__(self, "value", stripped)

    @property
    def normalized(self) -> str:
        # The display spelling is whatever the catalog sent ("Science-Fiction",
        # "DIY"), so it is kept as-is and every comparison — in memory here and
        # in the SQL filter — goes through this form instead.
        return self.value.casefold()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Genre):
            return NotImplemented
        return self.normalized == other.normalized

    def __hash__(self) -> int:
        return hash(self.normalized)
