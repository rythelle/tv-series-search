from application.dto.insight_dto import GenerateInsightInput, InsightResultOutput
from application.insight_cache_key import build_insight_cache_key
from application.insight_subject import resolve_insight_subject
from application.interfaces.comment_repository import CommentRepository
from application.interfaces.insight_cache import InsightCache
from application.interfaces.show_read_model_repository import ShowReadModelRepository


class GetCachedInsight:
    def __init__(
        self,
        show_repository: ShowReadModelRepository,
        comment_repository: CommentRepository,
        cache: InsightCache,
    ):
        self._show_repository = show_repository
        self._comment_repository = comment_repository
        self._cache = cache

    async def execute(self, input: GenerateInsightInput) -> InsightResultOutput | None:
        genres, summary, series_summary = await resolve_insight_subject(self._show_repository, input)
        comment_count, max_comment_id = await self._comment_repository.fingerprint(
            input.target_type, input.target_id
        )
        cache_key = build_insight_cache_key(
            input.target_type, input.target_id, genres, summary, comment_count, max_comment_id,
            series_summary=series_summary or "",
        )
        insight = await self._cache.get(cache_key)
        if insight is None:
            return None
        return InsightResultOutput(
            text=insight.text.value, source=insight.source, model=insight.model,
            generated_at=insight.generated_at,
        )
