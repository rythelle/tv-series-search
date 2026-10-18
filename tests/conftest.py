import os

import asyncpg
import pytest

from infrastructure.observability import request_context
from infrastructure.persistence.migration_runner import run_migrations

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://app:app@localhost:5432/tvseries_test")


def unreachable_database(exc: BaseException):
    """Skip — or, when CI demands a database, fail — on an unreachable Postgres.

    Skipping is right for `make test`, which runs with no database at all. It is
    wrong for the pipeline's integration stage: a run that silently skipped all
    50 tests exits 0 and reports green, so CI sets REQUIRE_TEST_DATABASE=1 and
    gets the connection error instead.
    """
    message = f"Postgres not reachable at {DATABASE_URL}: {exc}"
    if os.environ.get("REQUIRE_TEST_DATABASE") == "1":
        pytest.fail(message, pytrace=False)
    pytest.skip(message)


@pytest.fixture(autouse=True)
def _reset_request_id():
    # The request-id lives in a process-wide ContextVar. Sync tests that set it
    # would otherwise leak the value into later tests; reset it before each test
    # so get_request_id() starts from its None default.
    request_context._request_id_var.set(None)
    yield


@pytest.fixture
async def pg_pool():
    try:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2, timeout=2)
    except (OSError, asyncpg.PostgresError) as exc:
        unreachable_database(exc)
    yield pool
    await pool.close()


@pytest.fixture
async def clean_pool(pg_pool):
    await run_migrations(pg_pool)
    async with pg_pool.acquire() as conn:
        await conn.execute(
            "TRUNCATE shows, episodes, watch_marks, comments, insight_cache, outbox RESTART IDENTITY CASCADE"
        )
    return pg_pool
