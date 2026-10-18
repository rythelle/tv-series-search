from dataclasses import replace

import asyncpg

from application.interfaces.comment_repository import CommentRepository
from domain.entities.comment import Comment
from domain.value_objects.comment_body import CommentBody
from domain.value_objects.viewer_id import ViewerId


class PostgresCommentRepository(CommentRepository):
    def __init__(self, connection: asyncpg.Connection):
        self._connection = connection

    async def add(self, comment: Comment) -> Comment:
        new_id = await self._connection.fetchval(
            """
            INSERT INTO comments (target_type, target_id, viewer_id, body, created_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            comment.target_type, comment.target_id, comment.viewer_id.value,
            comment.body.value, comment.created_at,
        )
        return replace(comment, id=new_id)

    async def list_for_target(self, target_type: str, target_id: int, limit: int) -> list[Comment]:
        rows = await self._connection.fetch(
            """
            SELECT id, target_type, target_id, viewer_id, body, created_at FROM comments
            WHERE target_type = $1 AND target_id = $2
            ORDER BY created_at DESC LIMIT $3
            """,
            target_type, target_id, limit,
        )
        return [_row_to_comment(row) for row in rows]

    async def fingerprint(self, target_type: str, target_id: int) -> tuple[int, int]:
        row = await self._connection.fetchrow(
            """
            SELECT count(*) AS count, coalesce(max(id), 0) AS max_id FROM comments
            WHERE target_type = $1 AND target_id = $2
            """,
            target_type, target_id,
        )
        return (row["count"], row["max_id"])


def _row_to_comment(row: asyncpg.Record) -> Comment:
    return Comment(
        id=row["id"], target_type=row["target_type"], target_id=row["target_id"],
        viewer_id=ViewerId(str(row["viewer_id"])), body=CommentBody(row["body"]),
        created_at=row["created_at"],
    )
