"""The CI contract for the Postgres-backed suite.

A build where every `@pytest.mark.integration` test skipped is indistinguishable
from one where they all passed: both exit 0. CI therefore sets
`REQUIRE_TEST_DATABASE=1`, and under that flag an unreachable database has to
fail the run instead of skipping it.
"""

import pytest

from tests import conftest


def test_unreachable_database_skips_by_default(monkeypatch):
    monkeypatch.delenv("REQUIRE_TEST_DATABASE", raising=False)

    with pytest.raises(pytest.skip.Exception) as excinfo:
        conftest.unreachable_database(OSError("connection refused"))

    assert "connection refused" in str(excinfo.value)


def test_unreachable_database_fails_when_required(monkeypatch):
    monkeypatch.setenv("REQUIRE_TEST_DATABASE", "1")

    with pytest.raises(pytest.fail.Exception) as excinfo:
        conftest.unreachable_database(OSError("connection refused"))

    assert "connection refused" in str(excinfo.value)
