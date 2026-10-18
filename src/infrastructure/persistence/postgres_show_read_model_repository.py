import asyncpg

from application.dto.show_dto import PopularCursor
from application.interfaces.show_read_model_repository import ShowReadModelRepository
from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId

_SHOW_COLUMNS = (
    "id, name, premiered_year, poster_url, summary, genres, rating, "
    "popularity, details_fetched_at, episodes_fetched_at"
)
_EPISODE_COLUMNS = "id, show_id, season, number, name, airdate, runtime, summary"


class PostgresShowReadModelRepository(ShowReadModelRepository):
    def __init__(self, pool: asyncpg.Pool, word_similarity_threshold: float = 0.5):
        self._pool = pool
        self._word_similarity_threshold = word_similarity_threshold

    async def search(self, query: str, limit: int, genre: Genre | None = None) -> list[Show]:
        # `name %> $1` scores the query against the best matching extent of the
        # title, not against the whole string. similarity() compared whole
        # strings, so every word the query does not mention diluted the score:
        # "dext" rated "DEA" (0.29) above "Dexter: New Blood" (0.22), and a
        # threshold between them kept exactly the wrong one.
        #
        # The threshold rides in a GUC rather than a parameter because only the
        # operator reads shows_name_trgm_idx. Spelled as word_similarity($1,
        # name) > $2 the same filter is a seq scan that rescores every row:
        # 4.1s against 2k rows, versus 18ms. It is set local to the transaction
        # so it reverts before the connection goes back to the pool.
        sql = f"""
            SELECT {_SHOW_COLUMNS} FROM shows
            WHERE (search_vector @@ plainto_tsquery('simple', unaccent($1))
                   OR name %> $1)
              AND ($3::text IS NULL OR genres_normalized && ARRAY[$3]::text[])
            ORDER BY
                (ts_rank(search_vector, plainto_tsquery('simple', unaccent($1))) * 2
                 + word_similarity($1, name) + popularity / 100.0) DESC
            LIMIT $2
        """
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "SELECT set_config('pg_trgm.word_similarity_threshold', $1, true)",
                str(self._word_similarity_threshold),
            )
            rows = await conn.fetch(sql, query, limit, genre.normalized if genre else None)
        return [_row_to_show(row) for row in rows]

    async def list_popular(
        self, limit: int, after: PopularCursor | None = None, genre: Genre | None = None
    ) -> list[Show]:
        # `id` is not decoration: popularity comes from the TVMaze weight, a small
        # integer, so ties are everywhere. Ordering by popularity alone lets the
        # planner return tied rows in a different order per query, and a paged
        # read would then repeat or drop shows between pages.
        #
        # The page is taken by keyset rather than OFFSET because rows arrive while
        # readers are scrolling -- see PopularCursor. The predicate mirrors the
        # ORDER BY: popularity descends, so "after" means a lower popularity, and
        # within a tie it means a higher id.
        sql = f"""
            SELECT {_SHOW_COLUMNS} FROM shows
            WHERE ($4::text IS NULL OR genres_normalized && ARRAY[$4]::text[])
              AND ($2::double precision IS NULL
                   OR popularity < $2
                   OR (popularity = $2 AND id > $3))
            ORDER BY popularity DESC, id LIMIT $1
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                sql, limit,
                after.popularity if after else None,
                after.show_id if after else None,
                genre.normalized if genre else None,
            )
        return [_row_to_show(row) for row in rows]

    async def count_popular(self, genre: Genre | None = None) -> int:
        sql = """
            SELECT count(*) FROM shows
            WHERE $1::text IS NULL OR genres_normalized && ARRAY[$1]::text[]
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchval(sql, genre.normalized if genre else None)

    async def list_genres(self) -> list[Genre]:
        sql = """
            SELECT MIN(genre) AS genre, COUNT(*) AS shows_in_genre
            FROM shows, unnest(genres) AS genre
            GROUP BY lower(genre)
            ORDER BY shows_in_genre DESC, MIN(genre)
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql)
        return [Genre(row["genre"]) for row in rows]

    async def get_show(self, show_id: ShowId) -> Show | None:
        sql = f"SELECT {_SHOW_COLUMNS} FROM shows WHERE id = $1"
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, show_id.value)
        return _row_to_show(row) if row else None

    async def get_episodes(self, show_id: ShowId) -> list[Episode]:
        sql = f"SELECT {_EPISODE_COLUMNS} FROM episodes WHERE show_id = $1 ORDER BY season, number"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, show_id.value)
        return [_row_to_episode(row) for row in rows]

    async def get_episode(self, episode_id: EpisodeId) -> Episode | None:
        sql = f"SELECT {_EPISODE_COLUMNS} FROM episodes WHERE id = $1"
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, episode_id.value)
        return _row_to_episode(row) if row else None

    async def upsert_shows(self, shows: list[Show]) -> None:
        if not shows:
            return
        sql = """
            INSERT INTO shows (id, name, premiered_year, poster_url, summary, genres, rating,
                                popularity, details_fetched_at, episodes_fetched_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name, premiered_year = EXCLUDED.premiered_year,
                poster_url = EXCLUDED.poster_url, summary = EXCLUDED.summary,
                genres = EXCLUDED.genres, rating = EXCLUDED.rating, popularity = EXCLUDED.popularity,
                details_fetched_at = EXCLUDED.details_fetched_at,
                episodes_fetched_at = COALESCE(EXCLUDED.episodes_fetched_at, shows.episodes_fetched_at)
        """
        rows = [
            (
                show.id.value, show.name, show.premiered_year, show.poster_url, show.summary,
                [genre.value for genre in show.genres], show.rating, show.popularity,
                show.details_fetched_at, show.episodes_fetched_at,
            )
            for show in shows
        ]
        async with self._pool.acquire() as conn:
            await conn.executemany(sql, rows)

    async def upsert_episodes(self, show_id: ShowId, episodes: list[Episode]) -> None:
        if not episodes:
            return
        sql = """
            INSERT INTO episodes (id, show_id, season, number, name, airdate, runtime, summary)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            ON CONFLICT (id) DO UPDATE SET
                season = EXCLUDED.season, number = EXCLUDED.number, name = EXCLUDED.name,
                airdate = EXCLUDED.airdate, runtime = EXCLUDED.runtime, summary = EXCLUDED.summary
        """
        rows = [
            (episode.id.value, show_id.value, episode.season, episode.number, episode.name,
             episode.airdate, episode.runtime, episode.summary)
            for episode in episodes
        ]
        async with self._pool.acquire() as conn:
            await conn.executemany(sql, rows)


def _row_to_show(row: asyncpg.Record) -> Show:
    return Show(
        id=ShowId(row["id"]), name=row["name"], premiered_year=row["premiered_year"],
        poster_url=row["poster_url"], summary=row["summary"],
        genres=[Genre(name) for name in row["genres"]], rating=row["rating"],
        popularity=row["popularity"], details_fetched_at=row["details_fetched_at"],
        episodes_fetched_at=row["episodes_fetched_at"],
    )


def _row_to_episode(row: asyncpg.Record) -> Episode:
    return Episode(
        id=EpisodeId(row["id"]), show_id=ShowId(row["show_id"]), season=row["season"],
        number=row["number"], name=row["name"], airdate=row["airdate"],
        runtime=row["runtime"], summary=row["summary"],
    )
