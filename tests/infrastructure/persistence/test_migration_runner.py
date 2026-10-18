import pytest

from infrastructure.persistence.migration_runner import pending_migrations, run_migrations


def test_returns_unapplied_files_sorted():
    assert pending_migrations(["0002_x.sql", "0001_init.sql"], applied=set()) == [
        "0001_init.sql",
        "0002_x.sql",
    ]


def test_excludes_already_applied_files():
    assert pending_migrations(["0001_init.sql", "0002_x.sql"], applied={"0001_init.sql"}) == [
        "0002_x.sql",
    ]


def test_returns_empty_when_everything_is_applied():
    assert pending_migrations(["0001_init.sql"], applied={"0001_init.sql"}) == []


@pytest.mark.integration
async def test_running_migrations_twice_is_idempotent(pg_pool):
    await run_migrations(pg_pool)
    await run_migrations(pg_pool)  # must not raise

    async with pg_pool.acquire() as conn:
        tables = {
            row["tablename"]
            for row in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        }
    assert {"shows", "episodes", "watch_marks", "comments", "insight_cache", "outbox"} <= tables


@pytest.mark.integration
async def test_search_vector_tracks_accented_names_and_genres(pg_pool):
    await run_migrations(pg_pool)

    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO shows (id, name, genres) VALUES (999001, 'Série', ARRAY['Ação'])"
            )
            assert await conn.fetchval(
                "SELECT search_vector @@ plainto_tsquery('simple', 'serie acao') "
                "FROM shows WHERE id = 999001"
            )

            await conn.execute(
                "UPDATE shows SET name = 'Comédia', genres = ARRAY['Família'] WHERE id = 999001"
            )
            assert await conn.fetchval(
                "SELECT search_vector @@ plainto_tsquery('simple', 'comedia familia') "
                "FROM shows WHERE id = 999001"
            )
            assert not await conn.fetchval(
                "SELECT search_vector @@ plainto_tsquery('simple', 'serie acao') "
                "FROM shows WHERE id = 999001"
            )
            await conn.execute("DELETE FROM shows WHERE id = 999001")
