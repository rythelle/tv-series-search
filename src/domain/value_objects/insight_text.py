from dataclasses import dataclass


@dataclass(frozen=True)
class InsightText:
    value: str

    def __post_init__(self):
        if not self.value.strip():
            raise ValueError("insight text must not be blank")
