from abc import ABC, abstractmethod

from application.dto.insight_dto import InsightContext
from domain.entities.insight import Insight


class InsightGenerator(ABC):
    @abstractmethod
    async def generate(self, context: InsightContext) -> Insight: ...
