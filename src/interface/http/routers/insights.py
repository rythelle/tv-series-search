from typing import Literal

from fastapi import APIRouter, Response

from application.dto.insight_dto import GenerateInsightInput
from application.use_cases.generate_insight import GenerateInsight
from application.use_cases.get_cached_insight import GetCachedInsight
from interface.http.schemas.insight_schemas import InsightRequestSchema, InsightResponseSchema


def build_insights_router(
    generate_insight: GenerateInsight, get_cached_insight: GetCachedInsight
) -> APIRouter:
    router = APIRouter()

    @router.post("/insights", response_model=InsightResponseSchema)
    async def generate(body: InsightRequestSchema):
        result = await generate_insight.execute(
            GenerateInsightInput(target_type=body.target_type, target_id=body.target_id)
        )
        return InsightResponseSchema(
            text=result.text, generated_at=result.generated_at,
        )

    @router.get("/insights", response_model=InsightResponseSchema)
    async def peek(target_type: Literal["show", "episode"], target_id: int):
        result = await get_cached_insight.execute(
            GenerateInsightInput(target_type=target_type, target_id=target_id)
        )
        if result is None:
            return Response(status_code=204)
        return InsightResponseSchema(
            text=result.text, generated_at=result.generated_at,
        )

    return router
