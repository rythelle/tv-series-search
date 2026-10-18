from application.dto.insight_dto import GenerateInsightInput, InsightContext, InsightResultOutput
from application.insight_cache_key import build_insight_cache_key
from application.insight_subject import resolve_insight_subject
from application.interfaces.comment_repository import CommentRepository
from application.interfaces.insight_generator import InsightGenerator
from application.interfaces.show_read_model_repository import ShowReadModelRepository
from domain.entities.insight import Insight


class GenerateInsight:
    def __init__(
        self,
        show_repository: ShowReadModelRepository,
        comment_repository: CommentRepository,
        insight_generator: InsightGenerator,
        prompt_comment_count: int = 10,
    ):
        self._show_repository = show_repository
        self._comment_repository = comment_repository
        self._insight_generator = insight_generator
        self._prompt_comment_count = prompt_comment_count

    async def execute(self, input: GenerateInsightInput) -> InsightResultOutput:
        genres, summary, series_summary = await resolve_insight_subject(self._show_repository, input)
        comment_count, max_comment_id = await self._comment_repository.fingerprint(
            input.target_type, input.target_id
        )
        cache_key = build_insight_cache_key(
            input.target_type, input.target_id, genres, summary, comment_count, max_comment_id,
            series_summary=series_summary or "",
        )

        recent = await self._comment_repository.list_for_target(
            input.target_type, input.target_id, self._prompt_comment_count
        )
        context = InsightContext(
            target_type=input.target_type, target_id=input.target_id, cache_key=cache_key,
            genres=genres, summary=summary, recent_comments=[c.body.value for c in recent],
            series_summary=series_summary,
        )
        insight = await self._insight_generator.generate(context)
        return self._to_output(insight)

    def _to_output(self, insight: Insight) -> InsightResultOutput:
        return InsightResultOutput(
            text=insight.text.value, source=insight.source, model=insight.model,
            generated_at=insight.generated_at,
        )
