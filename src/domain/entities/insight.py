from dataclasses import dataclass
from datetime import datetime

from domain.value_objects.insight_text import InsightText


@dataclass
class Insight:
    text: InsightText
    source: str
    model: str | None
    generated_at: datetime
