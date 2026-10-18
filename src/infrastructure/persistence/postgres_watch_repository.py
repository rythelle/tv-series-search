import asyncpg

from application.interfaces.watch_repository import WatchRepository
from domain.entities.watch_mark import WatchMark
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId
from domain.value_objects.viewer_id import ViewerId


class PostgresWatchRepository(WatchRepository):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def mark(self, mark: WatchMark) -> None:
        sql = """
            INSERT INTO watch_marks (viewer_id, episode_id, watched_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (viewer_id, episode_id) DO NOTHING
        """
        async with self._pool.acquire() as conn:
            await conn.execute(sql, mark.viewer_id.value, mark.episode_id.value, mark.watched_at)

    async def unmark(self, viewer_id: ViewerId, episode_id: EpisodeId) -> None:
        sql = "DELETE FROM watch_marks WHERE viewer_id = $1 AND episode_id = $2"
        async with self._pool.acquire() as conn:
            await conn.execute(sql, viewer_id.value, episode_id.value)

    async def list_for_viewer(self, viewer_id: ViewerId, show_id: ShowId) -> set[EpisodeId]:
        sql = """
            SELECT wm.episode_id FROM watch_marks wm
            JOIN episodes e ON e.id = wm.episode_id
            WHERE wm.viewer_id = $1 AND e.show_id = $2
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, viewer_id.value, show_id.value)
        return {EpisodeId(row["episode_id"]) for row in rows}
