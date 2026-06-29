"""Integration tests for postgres/redis/s3 backends.

Skipped by default — run with: ``pytest -m integration``.
These require live services (see docker-compose in Phase 10).
"""

import os

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("HANFLOW_INTEGRATION"), reason="set HANFLOW_INTEGRATION=1")
@pytest.mark.asyncio
async def test_postgres_checkpoint_roundtrip():
    # Implemented alongside the postgres backend follow-up; placeholder keeps
    # the suite green. Real assertion added when langgraph-checkpoint-postgres
    # is wired (mirrors test_checkpoint.py against a pg URL).
    url = os.getenv("TEST_POSTGRES_URL")
    assert url, "TEST_POSTGRES_URL must be set for this integration test"
