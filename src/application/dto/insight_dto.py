from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GenerateInsightInput:
    target_type: str
    target_id: int


@dataclass
class InsightContext:
    target_type: str
    target_id: int
    cache_key: str
    genres: list[str]
    summary: str
    recent_comments: list[str] = field(default_factory=list)
    series_summary: str | None = None


@dataclass
class InsightResultOutput:
    text: str
    source: str
    model: str | None
    generated_at: datetime
