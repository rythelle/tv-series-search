from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def pending_migrations(available: list[str], applied: set[str]) -> list[str]:
    return sorted(name for name in available if name not in applied)


async def run_migrations(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        applied = {row["filename"] for row in await conn.fetch("SELECT filename FROM schema_migrations")}
        available = [path.name for path in sorted(MIGRATIONS_DIR.glob("*.sql"))]

        for filename in pending_migrations(available, applied):
            sql = (MIGRATIONS_DIR / filename).read_text()
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute("INSERT INTO schema_migrations (filename) VALUES ($1)", filename)
