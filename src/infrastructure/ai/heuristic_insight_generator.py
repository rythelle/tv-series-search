from application.dto.insight_dto import InsightContext
from application.interfaces.clock import Clock
from application.interfaces.insight_generator import InsightGenerator
from domain.entities.insight import Insight
from domain.services.insight_composition import compose_heuristic_insight
from domain.value_objects.insight_text import InsightText


class HeuristicInsightGenerator(InsightGenerator):
    def __init__(self, clock: Clock):
        self._clock = clock

    async def generate(self, context: InsightContext) -> Insight:
        subject_noun = "episode" if context.target_type == "episode" else "title"
        text = compose_heuristic_insight(
            genres=context.genres, summary=context.summary, comments=context.recent_comments,
            subject_noun=subject_noun,
        )
        return Insight(text=InsightText(text), source="fallback", model=None, generated_at=self._clock.now())
