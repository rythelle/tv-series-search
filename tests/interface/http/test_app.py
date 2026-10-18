import asyncio
import os

import asyncpg
import pytest
from fastapi.testclient import TestClient

from config import Settings
from interface.http.app import create_app

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://app:app@localhost:5432/tvseries_test")


def _database_reachable() -> bool:
    # Fast reachability probe so this test self-skips in ~2s on a DB-less machine,
    # instead of blocking on create_app's 30-attempt startup wait loop.
    async def _check() -> bool:
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=1, timeout=2)
        except (OSError, asyncpg.PostgresError):
            return False
        await pool.close()
        return True

    return asyncio.run(_check())


def test_the_app_boots_and_serves_health_and_ready():
    if not _database_reachable():
        pytest.skip(f"Postgres not reachable at {DATABASE_URL}")

    settings = Settings(DATABASE_URL=DATABASE_URL, AI_API_KEY="", SEED_ON_START=False)
    app = create_app(settings)
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        ready = client.get("/api/v1/ready")

    assert health.status_code == 200
    assert ready.status_code == 200
