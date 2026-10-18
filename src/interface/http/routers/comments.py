from fastapi import APIRouter, Header, status

from application.dto.comment_dto import ListCommentsInput, PostCommentInput
from application.use_cases.list_comments import ListComments
from application.use_cases.post_comment import PostComment
from interface.http.schemas.comment_schemas import (
    CommentSchema,
    CommentsListResponseSchema,
    PostCommentRequestSchema,
)


def build_comments_router(
    post_comment: PostComment, list_comments: ListComments, page_size: int,
) -> APIRouter:
    router = APIRouter()

    @router.get("/comments", response_model=CommentsListResponseSchema)
    async def list_comments_route(target_type: str, target_id: int):
        comments = await list_comments.execute(
            ListCommentsInput(target_type=target_type, target_id=target_id, limit=page_size)
        )
        return CommentsListResponseSchema(items=[CommentSchema.from_domain(c) for c in comments])

    @router.post("/comments", response_model=CommentSchema, status_code=status.HTTP_201_CREATED)
    async def post_comment_route(body: PostCommentRequestSchema, x_viewer_id: str = Header(...)):
        comment = await post_comment.execute(
            PostCommentInput(
                target_type=body.target_type, target_id=body.target_id,
                viewer_id=x_viewer_id, body=body.body,
            )
        )
        return CommentSchema.from_domain(comment)

    return router
