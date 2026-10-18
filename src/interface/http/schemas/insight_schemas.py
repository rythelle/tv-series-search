from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InsightRequestSchema(BaseModel):
    target_type: Literal["show", "episode"]
    target_id: int


class InsightResponseSchema(BaseModel):
    text: str
    generated_at: datetime
